
### Requirements ###
install:

    sudo apt install python3.12-venv
    sudo apt install python3-pip
    sudo apt install python3-wx*
    sudo apt-get install libgtk-3-dev
    sudo apt-get install libwebkit*

    sudo apt-get install build-essential

### Reference ###
https://tldp.org/LDP/abs/abs-guide.pdf


### Installation ###
* Install python3
    https://www.python.org/downloads/
* git clone https://github.com/scadding/MyUniverse_V2.git

## Virtual Environment ##
In some cases where there is a conflict or difficulty with the environment you may wish to use a virtual environment.

### Install venv as appropriate for your platform: ###
https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/

run:

    python3 -m venv .venv
    . .venv/bin/activate
    pip3 install -r requirements.txt


    ./MyUniverse.py

    deactivate

this may not be necesary:

    export PYTHONPATH=$PYTHONPATH:$PWD

### Testing ###

    ./src/Generators/tablegen/table.py --data=$PWD/Data --table=test
    ls -ltr test/
    ./src/Generators/tablegen/table.py --data=$PWD/Data --run=Test
    ./src/Generators/tablegen/table.py --test --data=$PWD/Data --groups
    ./src/Generators/tablegen/table.py --data=$PWD/Data --run=csv
    ./src/Generators/tablegen/table.py --data=$PWD/Data --group=csv
    ./src/Generators/tablegen/table.py --data=$PWD/Data --tables=csv

help:

    ./src/Generators/tablegen/table.py --help
    Usage: table.py [options]

    Options:
    -h, --help            show this help message and exit
    -d Data, --data=Data  Data Directory
    -a, --all             
    --test                
    -i, --import          
    -l, --listen          
    -s, --server          
    -t Table, --table=Table
                            Table Name
    -g Group, --group=Group
                            Group Name
    -r RUN, --run=RUN     
    --groups              
    --tables=TABLES       
  

