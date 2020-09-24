#!/bin/bash

sudo apt-get update
sudo apt-get install -y g++ nfs-common
MINICONDA=https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
QLIB_CLIENT=https://github.com/microsoft/qlib.git
STOCK_DATA_DIR=/data/stock_data/qlib_data

CODE_DIR=$HOME/"code"
DOWNLOADS_DIR=$HOME/"downloads"
CONDA_DIR=$HOME/"miniconda3"


# create dir
function create_dir_by_sudo() {
    if [ ! -d $1 ]; then
            sudo mkdir -p $1
    fi
}

function create_dir() {
    if [ ! -d $1 ]; then
            mkdir $1
    fi
}


create_dir $CONDA_DIR
create_dir $CODE_DIR
create_dir $DOWNLOADS_DIR
create_dir_by_sudo $STOCK_DATA_DIR

# install miniconda3
wget $MINICONDA -O $DOWNLOADS_DIR/"miniconda3.sh"
/bin/bash $DOWNLOADS_DIR/miniconda3.sh -b -u -p $CONDA_DIR

echo ". $CONDA_DIR/etc/profile.d/conda.sh" >> $HOME/.bashrc
echo "conda activate base" >> $HOME/.bashrc

# install qlib client
cd $CODE_DIR
git clone $QLIB_CLIENT
cd qlib
$CONDA_DIR/bin/pip install cython numpy
$CONDA_DIR/bin/python setup.py install
