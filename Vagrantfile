# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

$provisioning_script = <<SCRIPT
# Add Docker apt repo gpg key
apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys \
    58118E89F3A912897C070ADBF76221572C52609D
echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" > \
    /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-engine

# Build a version of Jupyter Notebook with all Aurum's dependencies and API
# code included.
cd /vagrant
docker build -t aurum-notebook .

# Check out and build a tweaked version of tmpnb which supports specifying the
# container network
cd ~
git clone https://github.com/datahuborg/tmpnb.git aurum-tmpnb
cd aurum-tmpnb
docker build -t aurum-tmpnb .

# Create a separate network for Jupyter notebooks to talk with elasticsearch.
# Block them from talking to anything else.
docker network create aurum
AURUM_LINK_NAME=br-$(docker network ls -q -f name=aurum)
iptables -I FORWARD 2 -i $AURUM_LINK_NAME -o eth0 -j REJECT

# Create a separate data container to persist elasticsearch's data.
docker create --name elasticsearch_data --entrypoint /bin/true elasticsearch:2.3
docker run -d --name elasticsearch --net=aurum --volumes-from elasticsearch_data elasticsearch:2.3

# Set up tmpnb and its proxy.
export TOKEN=$( head -c 30 /dev/urandom | xxd -p )
echo $TOKEN > ~/proxy_auth_token
docker run -d \
    --net=host \
    -e CONFIGPROXY_AUTH_TOKEN=$TOKEN \
    -u root \
    --name=proxy jupyter/configurable-http-proxy \
    --default-target http://127.0.0.1:9999 \
    --port 80 \
    --api-port 8001
docker run -d \
    --net=host \
    -e CONFIGPROXY_AUTH_TOKEN=$TOKEN \
    --name=tmpnb \
    -v /var/run/docker.sock:/docker.sock \
    aurum-tmpnb \
    python orchestrate.py --image='aurum-notebook' \
        --container_network='aurum' \
        --recaptcha_key='substitute_with_real_value' \
        --recaptcha_secret='substitute_with_real_value' \
        --redirect_uri='/notebooks/MIT_DWH_v4.ipynb' \
        --pool_size=10 \
        --mem-limit='512m' \
        --cpu_shares=12000 \
        --cull-period=600 \
        --cull-max=3600 \
        --cull-timeout=1800 \
        --command='start-notebook.sh \
            "--NotebookApp.base_url={base_path} \
            --ip=0.0.0.0 \
            --port={port} \
            --NotebookApp.trust_xheaders=True"'
SCRIPT

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/trusty64"

  config.vm.network "private_network", ip: "192.168.50.5"
  config.vm.hostname = "aurum-local.mit.edu"
  config.vm.provision "shell", inline: $provisioning_script

  config.vm.provider "virtualbox" do |vm|
    vm.name = "aurum-local"
    vm.memory = 2048
    #vm.cpus = 2
    # Set the timesync threshold to 1 minute, instead of the default 20 minutes.
    vm.customize ["guestproperty", "set", :id, "/VirtualBox/GuestAdd/VBoxService/--timesync-set-threshold", 60000]
  end
end
