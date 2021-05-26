import requests
import yaml
import json
import time
import random
import string
import boto3
import os
from python.kube import kube


class session():
    """Create the Kubernetes Cluster in Digital Ocean 

    Varibles:
        headers (dict): The headers for all api requests made to Digital Ocean API (includes auth token)
        settings (dict): Stores the settings for the deployemnt from settings.yaml
        kube (dict): Stores the details about the Kubernetes Cluster after its made
        mysql (dict): Stores the details about the MySQL DB after its made
        redis (int): Stores the details about the Redis DB after its made
        registry (int): Stores the about the Container Registry after its made
        boto (boto3.clinet): Stores the client for the boto3 library boto3 is the aws library and is used for DO Storage spaces
    """    

    headers = None
    settings = None
    kube = None
    mysql = None
    redis = None
    registry = None
    boto = None
    

    def __init__(self):

        # Read the settings and store them
        with open(r'settings.yaml') as file:
            self.settings = yaml.load(file, Loader=yaml.FullLoader)
        
        # Checks to see if there is a Kubernetes Cluster already configured
        try:
            with open('config/do/kube.json') as f:
                self.kube = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Checks to see if there is a MySQL DB already configured
        try:
            with open('config/do/mysql.json') as f:
                self.mysql = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Checks to see if there is a Redis DB already configured
        try:
            with open('config/do/redis.json') as f:
                self.redis = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass
        
        # Creates ther config DIrectory if it doesnt exists
        if not os.path.exists('config'):
            os.makedirs('config')
            os.makedirs('config/frontend')
            os.makedirs('config/backend')
            os.makedirs('config/do')

        # Checks to see if there is a Container Registry already configured
        try:
            with open('config/do/registry.json') as f:
                self.registry = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Sets the header for all api requests 
        api_key = self.settings['infra']["api_key"]
        self.headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
        }

        # Creates the boto3 client
        session = boto3.session.Session()
        self.boto = session.client('s3',
                        region_name='nyc3',
                        endpoint_url='https://nyc3.digitaloceanspaces.com',
                        aws_access_key_id=self.settings['infra']['storage']['spaceKey'],
                        aws_secret_access_key=self.settings['infra']['storage']['spaceSecret'])
    

    def createKube(self, region="tor1", count=1, size=1, scale=True, min_nodes=1, max_nodes=3):
        """Create the Kubernetes Cluster in Digital Ocean 

        Args:
            region (str, optional): The region that it will be deployed in. Defaults to "tor1".
            count (int, optional): The starting amount of nodes proably lleave at 1. Defaults to 1.
            size (int, optional): the size of the ndoe from 1-3. Defaults to 1.
            scale (bool, optional): do you want the cluster to autoscale. Defaults to True.
            min_nodes (int, optional): min nodes if autoscale true. Defaults to 1.
            max_nodes (int, optional): max nodes if auto scale true. Defaults to 3.
        """        
        # Getting the node Size Slug
        if size == 1:
            size = 's-1vcpu-2gb'
        elif size == 2:
            size = 's-2vcpu-2gb'
        elif size == 3:
            size = 's-2vcpu-4gb'
        
        # Creating the Payload for the api request
        data = {
            'name':'ctf',
            'region':f'{region}',
            'version':'latest',
            'tags':[
                'ctf',
            ],
            'node_pools':[
                {
                    'size': size,
                    'count':count,
                    'name':'ctf-pool',
                    'tags':[
                        'ctf'
                    ],
                    'labels':{
                        'service':'ctf',
                    },
                    'auto_scale': scale,
                    'min_nodes': min_nodes,
                    'max_nodes': max_nodes
                }
            ]
        }

        # Sends the API request to create the cluster
        res = requests.post("https://api.digitalocean.com/v2/kubernetes/clusters", json=data, headers=self.headers)

        #Stores the Kubernetes Cluster settings
        self.kube = json.loads(res.text)['kubernetes_cluster']
    
    def getCluster(self):
        """Gets the detail about a cluster including the kubeconfig file
        """

        # Gets the Cluster details and stores them
        res = requests.get(f"https://api.digitalocean.com/v2/kubernetes/clusters/{self.kube['id']}", headers=self.headers)
        self.kube = json.loads(res.text)['kubernetes_cluster']

        # Gets the kubeconfig file
        res = requests.get(f"https://api.digitalocean.com/v2/kubernetes/clusters/{self.kube['id']}/kubeconfig", headers=self.headers)
        self.kube['config'] = yaml.load(res.text, Loader=yaml.CLoader)
    
    def waitForCluster(self):
        """Waits for the cluster to be provisoned then install the nginx controller
        """

        # Creates the payload for the API request
        data = {
            "addon_slugs": [
                "ingress-nginx"
            ],
            "cluster_uuid": self.kube['id']
            }
        
        # Loops until the cluster is provisioned
        while True:
            # Gets the Cluster details
            self.getCluster()

            # Checks if the cluster is provisioned 
            if self.kube['status']['state'] != "provisioning":

                # Installs Nignx Controller in the cluster
                res = requests.post('https://api.digitalocean.com/v2/1-clicks/kubernetes', json=data, headers=self.headers)
                
                # Writes the config to a file
                with open('config/do/kube.json', 'w') as f:
                    f.write(json.dumps(self.kube))
                break

            # Waits to check again
            time.sleep(20)

    def createMysql(self, region='tor1', size=1, nodes=1):
        """Creates the MySQL database cluster

        Args:
            region (str, optional): The region the cluster will be in. Defaults to 'tor1'.
            size (int, optional): The size of the db nodes form 1-4. Defaults to 1.
            nodes (int, optional): The amount of db nodes. Defaults to 1.
        """

        # Selects the DB size slug
        if size == 1:
            size = 'db-s-1vcpu-1gb'
        elif size == 2:
            size = 'db-s-1vcpu-2gb'
        elif size == 3:
            size = 'db-s-2vcpu-4gb'
        elif size == 4:
            size = 'db-s-4vcpu-8gb'

        # Create the payload for the api request
        data = {
            "name": "frontend-mysql",
            "engine": "mysql",
            "region": region,
            "size": size,
            "num_nodes": nodes,
            "tags": 
            [
                "frontend"
            ]
        }

        # Call the api and store the response as the mysql details
        res = requests.post("https://api.digitalocean.com/v2/databases", json=data, headers=self.headers)
        self.mysql = json.loads(res.text)['database']
    
    def getMysql(self):
        """Gets the details of the mysql cluster form the API and stores it
        """        
        res = requests.get(f"https://api.digitalocean.com/v2/databases/{self.mysql['id']}", headers=self.headers)
        self.mysql = json.loads(res.text)['database']

    def waitForMysql(self):
        """Waits for the Mysql cluster to be ready and creates a new user with the older auth plugin for compatability with ctfd
        """

        # Create the payload for the API request
        data = {
            "name": "ctf-user",
            'mysql_settings':{
                'auth_plugin': 'mysql_native_password'
            }
            
        }

        # Loops until MySQL DB is provisined 
        while True:

            # Updates the Mysql details
            self.getMysql()

            # Checks if the DB is provisioned
            if self.mysql['status'] != "creating":

                # Creates the new user in the DB 
                res = requests.post(f"https://api.digitalocean.com/v2/databases/{self.mysql['id']}/users", json=data, headers=self.headers)
                res = json.loads(res.text)['user']

                # stores the new credentials in the DB details
                self.mysql['private_connection']['user'] = res['name']
                self.mysql['private_connection']['password'] = res['password']

                # Writes the details to a file
                with open('config/do/mysql.json', 'w') as f:
                    f.write(json.dumps(self.mysql))
                break

            # Delay inbetween checking the DB
            time.sleep(20)

    def createRedis(self, region='tor1', size=1, nodes=1):
        """Creates the Redis database cluster

        Args:
            region (str, optional): The region the cluster will be in. Defaults to 'tor1'.
            size (int, optional): The size of the db nodes form 1-4. Defaults to 1.
            nodes (int, optional): The amount of db nodes. Defaults to 1.
        """

        # Selects the DB size slug
        if size == 1:
            size = 'db-s-1vcpu-1gb'
        elif size == 2:
            size = 'db-s-1vcpu-2gb'
        elif size == 3:
            size = 'db-s-2vcpu-4gb'
        elif size == 4:
            size = 'db-s-4vcpu-8gb'
        
        # Create the payload for the api request
        data = {
            "name": "frontend-redis",
            "engine": "redis",
            "region": region,
            "size": size,
            "num_nodes": nodes,
            "tags": 
            [
                "frontend"
            ]
        }

        # Call the api and store the response as the Redis details
        res = requests.post("https://api.digitalocean.com/v2/databases", json=data, headers=self.headers)
        self.redis = json.loads(res.text)['database']

    def getRedis(self):
        """Gets the details on the Redis DB CLuster
        """
        res = requests.get(f"https://api.digitalocean.com/v2/databases/{self.redis['id']}", headers=self.headers)
        self.redis = json.loads(res.text)['database']

    def waitForRedis(self):
        """Waits for the Redis DB Cluster to be provisined
        """

        # Loops untill DB is provisoned
        while True:

            # Gets the Redis DB Details
            self.getRedis()
            
            # Checks if the DB is provisined 
            if self.redis['status'] != "creating":

                # Writes Redis Detaisl to a file 
                with open('config/do/redis.json', 'w') as f:
                    f.write(json.dumps(self.redis))
                break

            # Delay inbetween checking the DB
            time.sleep(20)

    def createRegistry(self):
        """Creates a container registry that has a name of ctf-{random string}
        """

        # Get all the lowercase letters and numbers as thats all the names support
        letters = string.ascii_lowercase + string.digits

        # Create Payload for api request
        data = {
            "name": f"ctf-{''.join(random.choice(letters) for i in range(10))}",
            "subscription_tier_slug": "basic"
        }

        # Call APi and store details
        res = requests.post("https://api.digitalocean.com/v2/registry", json=data, headers=self.headers)
        self.registry = json.loads(res.text)

    def waitForRegistry(self):
        """Function doesnt actully wait as container registry are almost instant,
        but it does get the docker creds for the registry and write the registry config to a file
        """
        # Calls API to get Registry Docker creds and stores them 
        res = requests.get('https://api.digitalocean.com/v2/registry/docker-credentials?read_write=true', headers=self.headers)
        self.registry['authJSON'] = json.loads(res.text)

        # Writes Registry details to a file
        with open('config/do/registry.json', 'w') as f:
            f.write(json.dumps(self.registry))
    
    def createSpace(self):
        """Creates a storage space with the name of the registry
        """        
        id = self.registry['registry']['name'].split('ctf-')[1]
        self.boto.create_bucket(Bucket=f'ctf-{id}')

    def uploadFile(self, path):
        """Uploads a file to the storage space

        Args:
            path (str): the path of the file that needs to be uloaded

        Returns:
            (str): The url opf the file
        """        

        # Gets the file name
        file = path.split('/')[-1:][0]
        
        # Gets the ID used for the storage space
        id = self.registry['registry']['name'].split('ctf-')[1]
        
        # Uploads the file to the space
        self.boto.upload_file(path, f'ctf-{id}', file, ExtraArgs={'ACL': 'public-read'})

        return f'https://ctf-{id}.nyc3.digitaloceanspaces.com{file}'

    def connectRegistry(self):
        """Enables integration between the container registry and the kubernetes cluster it also creates namespaces because that needs to be done before connecting
        """

        k = kube()

        # Deploys the frontend namespace
        k.createNamespace("templates/kubernetes/frontend/namespace.yaml")

        # Creates the backend namespace
        k.createNamespace('templates/kubernetes/backend/namespace.yaml')

        # Create the payload for the API request
        data = {
            "cluster_uuids": 
            [self.kube['id']]
        }

        # Call the API 
        res = requests.post('https://api.digitalocean.com/v2/kubernetes/registry', json=data, headers=self.headers)

    def createLB(self):
        """Creates a loadbalancer for the backend services
        """    

        data = {
        "name": "backend-lb",
        "region": "tor1",
        "size": "lb-small",
        "forwarding_rules": [],
        "health_check": {
            "protocol": "tcp",
            "port": 30000,
            "check_interval_seconds": 10,
            "response_timeout_seconds": 5,
            "healthy_threshold": 5,
            "unhealthy_threshold": 3
        },
        "sticky_sessions": {
            "type": "none"
        },
        "tag": "k8s:worker"
        }
        with open('config/backend/ports.yaml') as f:
            ports = yaml.load(f.read(), Loader=yaml.CLoader)

        for _, port in ports.items():
            data['forwarding_rules'].append({'entry_protocol': 'tcp', 'entry_port': port, 'target_protocol': 'tcp', 'target_port': port})

        res = requests.post('https://api.digitalocean.com/v2/load_balancers', json=data, headers=self.headers)

        with open('config/backend/lb.yaml', 'w') as f:
            f.write(yaml.dump(res.json(), Dumper=yaml.CDumper))

    def waitforLB(self):
        with open('config/backend/lb.yaml') as f:
            lb = yaml.load(f.read(), Loader=yaml.CLoader)

        time.sleep(5)
        while not lb['load_balancer']['ip']:
            id = lb['load_balancer']['id']
            res = requests.get(f'https://api.digitalocean.com/v2/load_balancers/{id}', headers=self.headers)
            lb = json.loads(res.text)
            time.sleep(15)
        
        print(lb)
        with open('config/backend/lb.yaml', 'w') as f:
            f.write(yaml.dump(res.json(), Dumper=yaml.CDumper))


    def deployInfra(self):
        """Deploys all the infrastucture needed
        """

        # Deploys the k8 cluster MySQL, Redis DBs and registry container
        self.createKube()
        self.createMysql()
        self.createRedis()
        self.createRegistry()

        # Waits for all the infrastucture to be provisoned 
        self.waitForRegistry()
        self.waitForCluster()
        self.waitForRedis()
        self.waitForMysql()

        # Connects the Registry and creates the storage space
        self.createSpace()
        self.connectRegistry()
        
