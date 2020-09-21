
#!/bin/bash


QLIB_SERVER=https://github.com/microsoft/qlib-server.git

STOCK_DATA_DIR=/data/stock_data/qlib_data

CODE_DIR=$HOME/"code"

function install_docker_in_ubuntu() {
    sudo apt-get update;
    sudo apt-get install apt-transport-https ca-certificates curl gnupg-agent software-properties-common;
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg |sudo apt-key add -;
    sudo apt-key fingerprint 0EBFCD88
    sudo add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable";
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io;
}


# install docker compose
function install_docker_compose() {
    sudo curl -L "https://github.com/docker/compose/releases/download/1.27.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
}

install_docker_in_ubuntu
install_docker_compose



# create dir
if [ ! -d "$CODE_DIR" ]; then
        mkdir $CODE_DIR
fi


if [ ! -d "$STOCK_DATA_DIR" ]; then
        sudo mkdir -p $STOCK_DATA_DIR
fi

# install qlib server
cd $CODE_DIR
git clone $QLIB_SERVER
cd qlib_server
sudo docker-compose build -f docker_support/docker_compose.yaml
sudo docker-compose up -d -f docker_support/docker_compose.yaml

