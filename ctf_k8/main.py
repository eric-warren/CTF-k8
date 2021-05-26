from python.digital_ocean import session
from python.kube import kube
from python.cloudflare import cf
from python.ctfd import ctfd
import yaml

s = session()
k = kube()
c = cf()
ctf = ctfd()

s.deployInfra()
k.deployFrontEnd()

k.createChallenges()

s.createLB()
s.waitforLB()
with open('config/backend/lb.yaml') as f:
    lb = yaml.load(f.read(), Loader=yaml.CLoader)
c.createRecord('chal', lb['load_balancer']['ip'])