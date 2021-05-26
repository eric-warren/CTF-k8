import requests
import random
import string
import yaml

class ctfd():

    settings = None

    def __init__(self):
        with open(r'settings.yaml') as file:
            self.settings = yaml.load(file.read(), Loader=yaml.FullLoader)

    def setup(self):
        domain = self.settings['domain']
        name = self.settings['ctf-name']
        desc = self.settings['ctf-description']
        if self.settings['mode'].lower() == 'team':
            mode = 'team_mode'
        else:
            mode = 'user_mode'
        user = 'admin'
        email = self.settings['admin-email']
        letters = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choice(letters) for i in range(15))
        data = f'''------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_name"

                {name}
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_description"

                {desc}
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="{mode}"

                users
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="name"

                {user}
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="email"

                {email}
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="password"

                {password}
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_logo"; filename=""
                Content-Type: application/octet-stream


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_banner"; filename=""
                Content-Type: application/octet-stream


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_small_icon"; filename=""
                Content-Type: application/octet-stream


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="ctf_theme"

                core
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="theme_color"


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="start"


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="start"


                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="_submit"

                Finish
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf
                Content-Disposition: form-data; name="nonce"

                9646e277dc25e281cea75364d83d4ffccf732f0e795a077fafd82b7511def93f
                ------WebKitFormBoundaryzZ74g4zylE33R6Rf--'''
