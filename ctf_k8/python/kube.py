from kubernetes import client, config
import yaml
import requests
import os
import time
from docker import client as dclient, from_env
import shlex
import json
from python.cloudflare import cf

class kube():
    """Create the Kubernetes Cluster in Digital Ocean 

    Varibles:
        core (kubernetes.client.CoreV1Api): Client for core kubernetws API
        app (kubernetes.client.AppsV1Api): Client for app kubernetes API
        networkbeta (kubernetes.client.NetworkingV1beta1Api): Client for networkbetav1 kubernetes API
        network (kubernetes.client.NetworkingV1Api): Client for networkv1 kubernetes API
        scale (kubernetes.client.AutoscalingV1Api): Client for autoscaling kubernetes API
        kube (dict): Details about kubernetes cluster
        settings (dict): Settings for the deployment
        mysql (dict): Details of the Mysql cluster
        redis (dict): Details of the Redis Cluster
        dclient (docker.client): Client for docker API
        ip (str): IP address of the ingress loadbalancer

    """    

    core = None
    app = None
    networkbeta = None
    network = None
    scale = None
    kube = None
    settings = None
    mysql = None
    redis = None
    dclient = None
    ip = None

    def __init__(self):
        """Loads all the clients and the settings if they can be loaded
        """

        # Loads the settings for the deployment
        with open(r'settings.yaml') as file:
            self.settings = yaml.load(file.read(), Loader=yaml.FullLoader)
            
        # Loads Kubernetes details if they exist
        try:
            with open('config/do/kube.json') as f:
                self.kube = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Loads mysql details if they exist
        try:
            with open('config/do/mysql.json') as f:
                self.mysql = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Loads redis details if they exist
        try:
            with open('config/do/redis.json') as f:
                self.redis = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Loads container registry details if they exist
        try:
            with open('config/do/registry.json') as f:
                self.registry = yaml.load(f.read(), Loader=yaml.CLoader)
        except:
            pass

        # Loads the kubeconfig into the pytohn kubernetes client
        try:
            config.load_kube_config_from_dict(self.kube['config'])
        except:
            pass
        
        

        # Loads all the Kubernetes clients
        self.app = client.AppsV1Api()
        self.core = client.CoreV1Api()
        self.networkbeta = client.NetworkingV1beta1Api()
        self.network = client.NetworkingV1Api()
        self.scale = client.AutoscalingV1Api()

        # Starts the docker client and logs into the registry
        self.dclient = from_env()
        key = self.settings['infra']['api_key']
        self.dclient.login(username=key, password=key, registry='registry.digitalocean.com')


    def createDeployment(self, file, ns):
        """Creates a Kubernetes Deployemnt

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """
        # Opens file and loads yaml file
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.app.create_namespaced_deployment(
            body=dep, namespace=ns)

    def createIngress(self, file, ns):
        """Creates a Kubernetes Ingress

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """

        time.sleep(5)
        # Sets the Headers for the API request
        headers = self.network.api_client.configuration.api_key

        # Opens file and loads yaml file
        with open(file) as f:
            dep = yaml.safe_load(f)

        # Calls the API
        res = requests.post(f'{self.network.api_client.configuration.host}/apis/networking.k8s.io/v1/namespaces/{ns}/ingresses', json=dep, headers=headers, verify=self.network.api_client.configuration.ssl_ca_cert)
        if res.status_code in [200, 201, 202]:
            print(res.status_code)
            self.createIngress(file, ns)

    def createNamespace(self, file):
        """Creates a Kubernetes Namespace

        Args:
            file (str): Path the the Kubernetes yaml file
        """

        # Opens file and loads yaml file 
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.core.create_namespace(
                body=dep
            )

    def createSecret(self, file, ns):
        """Creates a Kubernetes Secret

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """

        # Opens file and loads yaml file
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.core.create_namespaced_secret(
                body=dep, 
                namespace=ns
            )

    def createService(self, file, ns):
        """Creates a Kubernetes Service

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """

        # Opens file and loads yaml file 
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.core.create_namespaced_service(
                body=dep, 
                namespace=ns
            )

    def createAutoScaler(self, file, ns):
        """Creates a Kubernetes autoscaler

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """

        # Opens file and loads yaml file
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.scale.create_namespaced_horizontal_pod_autoscaler(
                body=dep, 
                namespace=ns
            )

    def createConfig(self, file, ns):
        """Creates a Kubernetes Config map

        Args:
            file (str): Path the the Kubernetes yaml file
            ns (str): The namespace to be deployed to
        """

        # Opens file and loads yaml file
        with open(file) as f:
            dep = yaml.safe_load(f)

            # Calls the API via the client
            resp = self.core.create_namespaced_config_map(
                body=dep, 
                namespace=ns
            )

    def waitForIngress(self):
        """Waits for ingress to get an ip address
        """

        # Loops untill ingress has an ip
        while True:

            # Sets the headers and get the ingress details from the API
            headers = self.network.api_client.configuration.api_key
            res = requests.get(f'{self.network.api_client.configuration.host}/apis/networking.k8s.io/v1/namespaces/frontend/ingresses/ctfd-frontend-ingress', headers=headers, verify=self.network.api_client.configuration.ssl_ca_cert)
            print(res.status_code)
            print(json.loads(res.text)['status'])
            # Checks if an ip has been assigned and stores in a file
            try:
                self.ip = json.loads(res.text)['status']['loadBalancer']['ingress'][0]['ip']
                with open('config/do/ingress.txt', 'w') as f:
                    f.write(self.ip)
                break
            except:
                pass

    def parseFrontSecret(self):
        """Perpares the yaml file form deployment
        """
        # Reads the Yaml file
        with open("templates/kubernetes/frontend/secret.yaml") as f:
            mani = yaml.load(f.read(), Loader=yaml.CLoader)

        # Loads all the values into the yaml file
        mani['data']['tls.crt'] = self.settings['ctfd']['tlsCert']
        mani['data']['tls.key'] = self.settings['ctfd']['tlsKey']

        # Writes the yaml file to be deployed 
        with open("config/frontend/secret.yaml", 'w') as f:
            f.write(yaml.dump(mani, Dumper=yaml.CDumper))
    
    def parseFrontDep(self):
        """Perpares the yaml file form deployment
        """
        # Reads the Yaml file
        with open("templates/kubernetes/frontend/dep.yaml") as f:
            mani = yaml.load(f.read(), Loader=yaml.CLoader)

        # Loads all the values into the yaml file
        mani['spec']['template']['spec']['containers'][0]['image'] = self.settings['ctfd']['image']
        user = self.mysql['private_connection']['user']
        password = self.mysql['private_connection']['password']
        port = self.mysql['private_connection']['port']
        host = self.mysql['private_connection']['host']
        uri = f'mysql+pymysql://{user}:{password}@{host}:{port}/defaultdb'
        mani['spec']['template']['spec']['containers'][0]['env'][1]['value'] = uri
        mani['spec']['template']['spec']['containers'][0]['env'][2]['value'] = self.redis['private_connection']['uri']

        # Writes the yaml file to be deployed 
        with open("config/frontend/dep.yaml", 'w') as f:
            f.write(yaml.dump(mani, Dumper=yaml.CDumper))

    def parseFrontScale(self):
        """Perpares the yaml file form deployment
        """
        # Reads the Yaml file
        with open("templates/kubernetes/frontend/scale.yaml") as f:
            mani = yaml.load(f.read(), Loader=yaml.CLoader)

        # Loads all the values into the yaml file
        mani['spec']['maxReplicas'] = self.settings['infra']['max-rep']
        mani['spec']['minReplicas'] = self.settings['infra']['min-rep']
        mani['spec']['targetCPUUtilizationPercentage'] = self.settings['infra']['CPU']

        # Writes the yaml file to be deployed 
        with open("config/frontend/scale.yaml", 'w') as f:
            f.write(yaml.dump(mani, Dumper=yaml.CDumper))
    
    def parseFrontIngress(self):
        """Perpares the yaml file form deployment
        """

        # Reads the Yaml file
        with open("templates/kubernetes/frontend/ingress.yaml") as f:
            mani = yaml.load(f.read(), Loader=yaml.CLoader)

        # Loads all the values into the yaml file
        mani['spec']['tls'][0]['hosts'][0] = self.settings['dns']['domain']
        mani['spec']['rules'][0]['host'] = self.settings['dns']['domain']

        # Writes the yaml file to be deployed
        with open("config/frontend/ingress.yaml", 'w') as f:
            f.write(yaml.dump(mani, Dumper=yaml.CDumper))
        

    def deployFrontEnd(self):
        """Deploys all of the Kubernetes needed to get CTFd up and running 
        """

        # runs init again so if the class was created before deploying the infra it will get all the configs
        self.__init__()

        # Sets the namespace string to pass into functions
        ns = "frontend"

        # Parses and deploys the cert secret
        self.parseFrontSecret()
        self.createSecret('config/frontend/secret.yaml', ns)

        # Parses and deploys the deployment
        self.parseFrontDep()
        self.createDeployment('config/frontend/dep.yaml', ns)

        # Parses and deploys the HPA
        self.parseFrontScale()
        self.createAutoScaler('config/frontend/scale.yaml', ns)

        # Deploys the service
        self.createService('templates/kubernetes/frontend/service.yaml', ns)

        # Parses and deploys the ingress
        self.parseFrontIngress()
        self.createIngress('config/frontend/ingress.yaml', ns)

        # Waits for the ingress to get an IP
        self.waitForIngress()

        # Deploys the DNS Record
        cfs = cf()
        cfs.createRecord()
        

    def deployChallenge(self, file, settings, count):
        """Deploys a single challenege (needs updateing will comment after)

        Args:
            file (str): the challenege folder
            settings (dict): the challeneg settings
            count (int): the index of the challenege
        """

        # Loads the Container registry name and the name of the challenege
        reg_name = self.registry['registry']['name']
        chal_name = settings['name']

        # Builds the docker image for the challenege
        image = self.dclient.images.build(path=f'{file}/deploy/', tag=f'registry.digitalocean.com/{reg_name}/{chal_name}', nocache=True)
        image[0].collection.push(f'registry.digitalocean.com/{reg_name}/{chal_name}')

        # Loads the Yaml file for the deployment
        with open('templates/kubernetes/backend/dep.yaml') as f:
            dep = yaml.load(f.read(), Loader=yaml.FullLoader)

        # Sets all the values needed
        dep['metadata']['name'] = f'ctf-backend-{chal_name}'
        dep['metadata']['labels']['app'] = f'ctf-{chal_name}'
        dep['spec']['selector']['matchLabels']['app'] = f'ctf-{chal_name}'
        dep['spec']['template']['metadata']['labels']['app'] = f'ctf-{chal_name}'
        dep['spec']['template']['spec']['containers'][0]['name'] =  f'ctf-{chal_name}'
        dep['spec']['template']['spec']['containers'][0]['image'] = f'registry.digitalocean.com/{reg_name}/{chal_name}:latest'
        dep['spec']['template']['spec']['containers'][0]['livenessProbe']['exec']['command'] = shlex.split(settings['liveCommand'], posix=False)
        
        # Writes the Yaml file for the deployment
        with open(f'{file}/dep.yaml', 'w') as f:
            f.write(yaml.dump(dep, Dumper=yaml.CDumper))

        # Reads the yaml file for the service
        with open('templates/kubernetes/backend/service.yaml') as f:
            ser = yaml.load(f.read(), Loader=yaml.FullLoader)

        # Loads the right values for the Yaml file
        ser['metadata']['name'] = f'ctf-{chal_name}-service'
        ser['spec']['selector']['app'] = f'ctf-{chal_name}'
        ser['spec']['ports'][0]['targetPort'] = settings['docker-port']
        ser['spec']['ports'][0]['nodePort'] = 30000 + count
        
        #Write the Yaml file for the service
        with open(f'{file}/ser.yaml', 'w') as f:
            f.write(yaml.dump(ser, Dumper=yaml.CDumper))

        with open('config/backend/ports.yaml', 'a') as f:
            f.write(f'{chal_name}: {30000+count}\n')

        # Creates the deployment and service 
        self.createDeployment(f'{file}/dep.yaml', 'backend')
        self.createService(f'{file}/ser.yaml', 'backend') 



    def createChallenges(self):
        """Creates all the challeneges and deploys them
        """

        # Loops through all the challeneges
        for count ,dir in enumerate(os.listdir('challeneges')):
            dir = f'challeneges/{dir}'
            # Opens the challeneges config file and loads it
            with open(f'{dir}/chal.yaml') as f:
                chal = yaml.load(f.read(), Loader=yaml.CLoader)

            # Deploys the challenege if needed
            if chal['needs-deployed']:
                self.deployChallenge(dir, chal, count)

