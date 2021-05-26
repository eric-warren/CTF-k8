import CloudFlare
import yaml

class cf():

    session = None
    zone = None
    ingress = None

    def __init__(self):
        with open(r'settings.yaml') as file:
            self.settings = yaml.load(file.read(), Loader=yaml.FullLoader)

        try:
            with open('config/do/ingress.txt') as f:
                self.ingress = f.read()
        except:
            pass

        self.session = CloudFlare.CloudFlare(token=self.settings['dns']['api_key'])
        self.getZones()

    def getZones(self):
        zones = self.session.zones.get()
        for zone in zones:
            if zone['name'] == self.settings['dns']['domain']:
                self.zone = zone
    
    def createRecord(self, domain='@', ip=None):
        self.__init__()
        if ip == None:
            ip = self.ingress
        record = {'name':f'{domain}', 'type':'A', 'content':ip}
        r = self.session.zones.dns_records.post(self.zone['id'], data=record)
    