# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import copy
import fire
import json
import yaml
import subprocess
from pathlib import Path
from typing import Iterable

from loguru import logger
from fabric2 import Connection, Config


QLIB_DATA_DIR = "/data/stock_data/qlib_data"
CUR_DIR = Path(__file__).resolve().parent

OFFLINE_CONFIG = {
    "provider_uri": QLIB_DATA_DIR,
    "region": "cn",
}


ONLINE_CONFIG = {
    # data provider config
    "calendar_provider": {"class": "LocalCalendarProvider", "kwargs": {"remote": True}},
    "instrument_provider": "ClientInstrumentProvider",
    "feature_provider": {"class": "LocalFeatureProvider", "kwargs": {"remote": True}},
    "expression_provider": "LocalExpressionProvider",
    "dataset_provider": "ClientDatasetProvider",
    "provider": "ClientProvider",
    # config it in user's own code
    "provider_uri": QLIB_DATA_DIR,
    # cache
    # Using parameter 'remote' to announce the client is using server_cache, and the writing access will be disabled.
    "expression_cache": None,
    "dataset_cache": None,
    "calendar_cache": None,
    "mount_path": QLIB_DATA_DIR,
    "auto_mount": True,  # The nfs is already mounted on our server[auto_mount: False].
    "flask_server": "127.0.0.1",
    "flask_port": 9710,
    "region": "cn",
}


class VMManager:
    REG_CN = "cn"
    REG_OTHER = "other"

    def __init__(self, vm_list_info):
        self.vm_list = []
        for info in vm_list_info:
            self.vm_list.append(VM(info))

    def list(self, only_running):
        for vm in self.vm_list:
            if not only_running or vm.is_running():
                yield vm.get_info()

    def list_ip(self, ip_type="private"):
        for vm in self.vm_list:
            yield vm.get_ip(ip_type=ip_type)


class VM:
    DEALLOC = "VM deallocated"
    RUNNING = "VM running"

    def __init__(self, info):
        self._info = info

    def is_running(self):
        return self._info["powerState"] == self.RUNNING

    def show(self):
        print(f"{self._info['name']}:{self._info['powerState']}")

    def get_info(self):
        return f"{self._info['name']}:{self._info['powerState']}"

    def get_ip(self, ip_type="private"):
        network = self._info["virtualMachine"]["network"]
        return (
            self._info["virtualMachine"]["name"],
            network["privateIpAddresses"][0] if ip_type == "private" else network["publicIpAddresses"][0]["ipAddress"],
        )


class Remote:
    def __init__(self, host, user, password=None, ssh_private_key=None):
        """
        Args:
            host (str): server host
            user (str): user name
            password (str): password, default None; If password is None, use ssh_key.
            ssh_private_key (Path, str): ssh public key path, default None; If ssh_key is None, use password.
        """
        self._host = host
        self._user = user
        if password is None and ssh_private_key is None:
            logger.warning("ssh_private_key and password are both none, ssh_private_key will use `~/.ssh/id_rsa`!")
            ssh_private_key = str(Path("~/.ssh/id_rsa").expanduser().resolve())

        if ssh_private_key is not None:
            ssh_key = str(Path(ssh_private_key).expanduser().resolve())
            connect_kwargs = {"key_filename": ssh_key}
            self.conn = Connection(host=self._host, user=self._user, connect_kwargs=connect_kwargs)
        else:
            config = Config(overrides={"sudo": {"password": password}})
            connect_kwargs = {"password": password}
            self.conn = Connection(host=self._host, user=self._user, connect_kwargs=connect_kwargs, config=config)

        self._home_dir = None

    @property
    def home_dir(self):
        if self._home_dir is None:
            self._home_dir = self.run("pwd", hide="stdout").stdout.strip()
        return self._home_dir

    def _execute_remote_shell(self, files, remote_dir=None):
        if remote_dir is None:
            remote_dir = self.home_dir
        self.mkdir_remote(remote_dir)
        if not isinstance(files, Iterable):
            files = [files]

        for file_path in map(lambda x: Path(x), files):
            self.put(str(file_path), remote_dir)
            # NOTE: This place may require a password
            # Consider using `self.conn.sudo(f"/bin/bash /home/{user}/{shell_path.name}")` instead
            self.run(f"/bin/bash {remote_dir}/{file_path.name}")

    def _dump_remote_yaml(self, obj, remote_file_path="tmp.yaml"):
        r_dir, r_name = os.path.split(remote_file_path)
        if r_dir.startswith("~"):
            r_dir = f"{self.home_dir}{r_dir[1:]}"
        # create tmp file in local
        _temp_dir = CUR_DIR.joinpath("tmp")
        _temp_dir.mkdir(parents=True, exist_ok=True)
        temp_client_path = _temp_dir.joinpath(r_name)
        with temp_client_path.open("w") as fp:
            yaml.dump(obj, fp)
        # create remote dir
        self.mkdir_remote(r_dir)
        self.put(str(temp_client_path), r_dir)
        # delete tmp file
        temp_client_path.unlink()

    def deploy_qlib_client(self, client_config=None):
        """deploy qlib clinet

        Args:
            client_config (dict): qlib client config
        """
        if client_config is None:
            raise ValueError("client_config cannot None")

        shell_path = CUR_DIR.joinpath("install_qlib_client.sh")
        self._execute_remote_shell(shell_path)
        self._dump_remote_yaml(client_config, "~/qlib_client_config.yaml")

    def deploy_qlib_server(self, client_config=None):
        """deploy qlib server

        Args:
            client_config (dict): qlib client config
        """

        shell_path_client = CUR_DIR.joinpath("install_qlib_client.sh")
        shell_path_server = CUR_DIR.joinpath("install_qlib_server.sh")
        self._execute_remote_shell((shell_path_client, shell_path_server))
        # Download default China Stock data
        self.run_python(
            f"{self.home_dir}/code/qlib/scripts/get_data.py qlib_data_cn --target_dir {QLIB_DATA_DIR}", sudo=True
        )

        if client_config is not None:
            client_config = copy.deepcopy(client_config)
            client_config["provider_uri"] = client_config["mount_path"]
            client_config["auto_mount"] = False
            self._dump_remote_yaml(client_config, "~/qlib_client_config.yaml")

    def run(self, command, hide=None):
        """run command in remote server

        Parameters
        ---------
        command : str
            command
        hide : bool, str
            hide shell stdout or stderr, value from stdout/stderr/True(stdout and stderr)/None(False), default None
        """
        logger.info(f"remote {self._user}@{self._host} running command: {command}")
        return self.conn.run(command, hide=hide)

    def put(self, local_path, remote_dir):
        """put file to remote

        Parameters
        ----------
        local_path: str
            local file path
        remote_dir: str
            remote dir
        """
        logger.info(f"putting {local_path} ot {self._user}@{self._host}:{remote_dir}")
        self.conn.put(local_path, remote_dir)

    def run_python(self, command, hide=True, sudo=False):
        """run python command

        Parameters
        ----------
        command : str
            python command
        hide : bool, str
            hide shell stdout or stderr, value from stdout/stderr/True, default True
        sudo : bool
            sudo command
        """
        # FIXME: hard code, fabric cannot use `~/.bashrc` PATH
        python_path = self.run(
            f"source {self.home_dir}/miniconda3/etc/profile.d/conda.sh; conda activate base; which python", hide=True
        ).stdout.strip()
        command = f"{python_path} {command}"
        if sudo:
            command = f"sudo {command}"
        return self.run(command, hide=hide)

    def mkdir_remote(self, dir_path, sudo=True):
        """mkdir dir in remote

        Parameters
        ----------
        dir_path : str
            remote dir path
        sudo : bool
            use sudo, value from True or False, by default True
        """
        if sudo:
            self.run(f"if [ ! -d {dir_path} ]; then sudo mkdir -p {dir_path}; fi")
        else:
            self.run(f"if [ ! -d {dir_path} ]; then mkdir -p {dir_path}; fi")


class CommandManager:
    def __init__(self, conf_path="azure_conf.yaml", region=VMManager.REG_OTHER):
        """

        Parameters
        ----------
        conf_path : str, optional
            azure config path, by default './azure_conf.yaml'

                sub_id: <Subscription ID>
                username: <azure username>
                password: <azure password>
                resource_group: <resource group name>

        region : str, optional
            azure region "cn" or "us", by default "cn"

        Raises
        ------
        ValueError
            Invalid credential
        ValueError
            Invalid set subscription
        """
        conf_path = Path(conf_path).expanduser().resolve()
        with conf_path.open() as f:
            conf = yaml.load(f, Loader=yaml.FullLoader)

        self.sub_id = conf["sub_id"]
        self.username = conf["username"]
        self.password = conf["password"]
        self.resource_group = conf["resource_group"]

        if region == VMManager.REG_CN:
            # NOTE: China needs to be set `AzureChinaCloud` to login successfully
            subprocess.run("az cloud set -n AzureChinaCloud", shell=True)

        if subprocess.run("az account show", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            login_cmd = f"az login -u '{self.username}' -p '{self.password}'"
            subprocess.check_call(login_cmd, shell=True, stdout=subprocess.DEVNULL)

        set_subscription_cmd = f"az account set --subscription {self.sub_id}"
        subprocess.check_call(set_subscription_cmd, shell=True, stdout=subprocess.DEVNULL)

    def _azure_run(self, command, output=False, stdout=None, stderr=None):
        """run command in azure-cli

        Parameters
        ----------
        command : str
            shell command
        """
        if not command.startswith("az "):
            command = f"az {command}"
        command = f"{command} -g {self.resource_group}"
        logger.info(f"running: {command}")
        return subprocess.check_output(command, shell=True) if output else subprocess.run(command, shell=True, stdout=stdout, stderr=stderr)

    def start(self, *vm_names):
        """start vm

        Examples
        ----------

            start vm1 vm2 vm3
            $ python azure_manager.py start vm1 vm2 vm3 --config_path azure_conf.yaml

            start vm in "cn"
            $ python azure_manager.py start vm1 vm2 vm3 --config_path azure_conf.yaml --region cn

        Parameters
        ----------
        vm_names : tuple
            vm names
        """
        logger.info(vm_names)
        for name in vm_names:
            self._azure_run(f"vm start -n {name}")

    def stop(self, *vm_names):
        """stop vm

        Examples
        ----------

            stop vm1 vm2 vm3
            $python azure_manager.py stop vm1 vm2 vm3 --config_path azure_conf.yaml

            stop vm in "cn"
            $python azure_manager.py stop vm1 vm2 vm3 --config_path azure_conf.yaml --region cn

        Parameters
        ----------
        vm_names : tuple
            vm names
        """

        logger.info(vm_names)
        for name in vm_names:
            self._azure_run(f"vm deallocate -n {name}")

    def _list(self, only_running=False):
        output = self._azure_run(f"vm list -d", output=True)
        ret = json.loads(output)
        vmm = VMManager(ret)
        for vm in vmm.list(only_running=only_running):
            yield vm

    def _list_ip(self, vm_name=None, ip_type="private"):
        logger.info(f"ip_type={ip_type}")
        cmd_str = "vm list-ip-addresses"
        if vm_name is not None:
            cmd_str = f"{cmd_str} --name {vm_name}"

        output = self._azure_run(cmd_str, output=True)
        ret = json.loads(output)
        vmm = VMManager(ret)
        for vm in vmm.list_ip(ip_type=ip_type):
            yield vm

    def list_ip(self, vm_names=None, ip_type="private"):
        """list all servers ip

        Parameters
        ----------
        vm_names : str, optional
            vm names, use "," to separate multiple names, such as: vm1,vm2,vm3
        ip_type : str, optional
            value from "private"/"public", by default "private"
        """
        for _ip in self._list_ip(vm_name=vm_names, ip_type=ip_type):
            print(_ip)

    def list(self, only_running=False):
        """show all vm names

        Examples
        ----------
            list all vm names
            $python azure_manager.py list --config_path azure_conf.yaml

            list vm names only runing
            $python azure_manager.py list --only_running --config_path azure_conf.yaml --region cn

        Parameters
        ----------
        only_running : bool, optional
            only show runing, by default False

        """
        logger.info(f"only_running={only_running}")
        for vm in self._list(only_running):
            print(vm)

    def view(self):
        """view all vm info

        Exampples
        ---------
            $ python azure_manager.py view --config_path azure_conf.yaml

            $ python azure_manager.py view --only_running --config_path azure_conf.yaml --region cn

        """
        self._azure_run("vm list -d")

    def create_vm(
        self,
        vm_names,
        admin_username,
        image="Canonical:UbuntuServer:18.04-LTS:latest",
        size="Standard_E64s_v3",
        vnet_name=None,
        nsg=None,
        public_ip_address_allocation="static",
        ssh_key_value=None,
        admin_password=None,
    ):
        """create vms

        NOTE
        ----
        Specific document reference for all parameters in the function: https://docs.microsoft.com/en-us/cli/azure/vm?view=azure-cli-latest#az_vm_create

        Examples
        ---------
            $ python azure_manager.py create_vm  --vm_names vm1,vm2,vm3 --admin_username test --ssh_key_value ~/.ssh/id_rsa.pub --config_path ./azure_conf.yaml

            $ python azure_manager.py create_vm --vm_names vm_server --admin_username test --ssh_key_value ~/.ssh/id_rsa.pub --config_path ./azure_conf.yaml

        Parameters
        ----------
        vm_names : str
            vm names, use "," to separate multiple names, such as: vm1,vm2,vm3
        image : str, optional
            az vm image list, by default `Canonical:UbuntuServer:18.04-LTS:latest`; value from: az vm image list
        admin_username : str, optional
            admin user name, by default None
        size : str, optional
            The VM size to be created. See https://azure.microsoft.com/pricing/details/virtual-machines/ for size info, by default `Standard_E64s_v3`
            Value from: az vm list-sizes
        vnet_name : str, optional
            Name of the virtual network when creating a new one or referencing an existing one, by default None
        nsg : str, optional
            The name to use when creating a new Network Security Group (default) or referencing an existing one, by default None
        public_ip_address_allocation : str, optional
            Accepted values: dynamic, static, by default "static"
        ssh_key_value : str, optional
            ssh public key file paths, by default None
        admin_password : str, optional
            Password for the VM if authentication type is 'Password', by default None

        """

        if ssh_key_value is None and admin_password is None:
            logger.error("ssh_key_value and admin_password cannot be none at the same time!")
            return
        shell = f"vm create --image {image} --size {size} --admin-username {admin_username} --public-ip-address-allocation {public_ip_address_allocation} "
        if vnet_name:
            shell += f"--vnet-name {vnet_name} "
        if nsg:
            shell += f"--nsg {nsg} "
        if ssh_key_value:
            ssh_key_path = Path(ssh_key_value).expanduser().resolve()
            if ssh_key_path.exists():
                ssh_key_value = str(ssh_key_path)
            shell += f"--ssh-key-value {ssh_key_value} "
        if admin_password:
            shell += f"--admin-password {admin_password} "

        for name in vm_names.split(","):
            name = name.strip()
            logger.info(f"create vm: {name}...")
            self._azure_run(shell + f"-n {name}")
            logger.info(f"create vm finished: {name}")

    def create_qlib_cs_vm(
        self,
        qlib_server_name=None,
        qlib_client_names=None,
        image="Canonical:UbuntuServer:18.04-LTS:latest",
        admin_username=None,
        size="Standard_E64s_v3",
        vnet_name=None,
        nsg=None,
        public_ip_address_allocation="static",
        ssh_key_value=None,
        admin_password=None,
        ssh_private_key=None,
    ):
        """create qlib client/server vm

        NOTE
        ----
        Specific document reference for all parameters in the function: https://docs.microsoft.com/en-us/cli/azure/vm?view=azure-cli-latest#az_vm_create

        Examples
        --------
            Create qlib-server and qlib-client using admin_password
            $ python azure_manager.py create_qlib_cs_vm --qlib_server_name CPU-Server01 --qlib_client_names CPU-Client01,CPU-Client02 --admin_username tmp_user --admin_password temp_user --conf_path ./azure_conf.yaml
            Create offline qlib-client
            $ python azure_manager.py create_qlib_cs_vm --qlib_client_names CPU-Client01,CPU-Client02 --admin_username tmp_user --admin_password temp_user --conf_path ./azure_conf.yaml
            Create vm using ssh-public-key
            $ python azure_manager.py create_qlib_cs_vm --qlib_client_names CPU-Client01,CPU-Client02 --admin_username tmp_user --ssh_key_value ~/.ssh/id_rsa.pub --conf_path ./azure_conf.yaml


        Parameters
        ----------
        qlib_server_name : str, optional
            VM name of qlib server, by default None.
            If `qlib_server_name` is `None`, qlib_client_names will create "offline-qlib".
            If the VM of `qlib_server_name` does not exist, it will be created.
        qlib_client_names : str, optional
            qlib client VM names, use "," to separate multiple names, such as: vm1,vm2,vm3. By default None.
            If `qlib_client_names` is None, qlib-client VM will not be created.
        image : str, optional
            az vm image list, by default `Canonical:UbuntuServer:18.04-LTS:latest`; value from: az vm image list
        admin_username : str, optional
            admin user name, by default None
        size : str, optional
            The VM size to be created. See https://azure.microsoft.com/pricing/details/virtual-machines/ for size info, by default `Standard_E64s_v3`
            Value from: az vm list-sizes
        vnet_name : str, optional
            Name of the virtual network when creating a new one or referencing an existing one, by default None
        nsg : str, optional
            The name to use when creating a new Network Security Group (default) or referencing an existing one, by default None
        public_ip_address_allocation : str, optional
            Accepted values: dynamic, static, by default "static"
        ssh_key_value : str, optional
            ssh public key file paths, by default None
        admin_password : str, optional
            Password for the VM if authentication type is 'Password', by default None
        ssh_private_key : str, optional
            ssh private key, by default None
        """

        if qlib_server_name is None and qlib_client_names is None:
            logger.error("qlib_server_name and qlib_client_names must exist at the same time")
            return

        def _create_vm(vm_name):
            if not any(map(lambda x: vm_name in x, self._list(only_running=False))):
                # create vm
                self.create_vm(
                    vm_names=vm_name,
                    image=image,
                    admin_username=admin_username,
                    size=size,
                    vnet_name=vnet_name,
                    nsg=nsg,
                    public_ip_address_allocation=public_ip_address_allocation,
                    ssh_key_value=ssh_key_value,
                    admin_password=admin_password,
                )
            else:
                logger.info(f"{vm_name} already exists, no longer create.")

        if qlib_server_name is None:
            # create offline qlib client
            client_config = {}

        else:
            # create qlib server
            _create_vm(qlib_server_name)
            # create online qlib client
            private_server_ip = list(self._list_ip(qlib_server_name))[0][-1]
            public_server_ip = list(self._list_ip(qlib_server_name, ip_type="public"))[0][-1]
            client_config = copy.deepcopy(ONLINE_CONFIG)
            client_config["flask_server"] = private_server_ip
            client_config["provider_uri"] = f"{private_server_ip}:/"
            logger.info(f"{qlib_server_name}: install qlib server......")
            Remote(
                host=public_server_ip, user=admin_username, password=admin_password, ssh_private_key=ssh_private_key
            ).deploy_qlib_server(client_config=client_config)
            logger.info(f"{qlib_server_name}: install qlib server successful.")

        if qlib_client_names is not None:
            # create qlib client
            for vm in qlib_client_names.split(","):
                _create_vm(vm)
                logger.info(f"{vm}: install qlib clinet......")
                Remote(
                    host=list(self._list_ip(vm, ip_type="public"))[0][-1],
                    user=admin_username,
                    password=admin_password,
                    ssh_private_key=ssh_private_key,
                ).deploy_qlib_client(client_config=client_config)
                logger.info(f"{vm}: install qlib client successful.")


if __name__ == "__main__":
    fire.Fire(CommandManager)
