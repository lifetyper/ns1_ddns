import ipaddress
import json
from argparse import ArgumentParser

import dns
import requests
from dns.resolver import Resolver
from ns1 import NS1


class DDNSUpdater(object):
    def __init__(self, domain: str, ns1_token: str, pushover_user_key: str,
                 pushover_api_token: str, ip_api_url: str, dns_server: str):
        self.domain = domain
        self.ns1_token = ns1_token
        self.pushover_user_key = pushover_user_key
        self.pushover_api_token = pushover_api_token
        self.ip_api_url = ip_api_url
        self.dns_server = dns_server

    def send_message(self, message):
        if all([self.pushover_user_key, self.pushover_api_token]):
            payload = {"message": message, "user": self.pushover_user_key, "token": self.pushover_api_token}
            response = requests.post('https://api.pushover.net/1/messages.json', data=payload,
                                     headers={'User-Agent': 'Python'})
            return response
        else:
            print("No API Token Provided!")
            return None

    def query_ip_for_domain(self) -> str:
        res = Resolver(configure=False)
        res.nameservers = [self.dns_server]
        r = res.resolve(qname=self.domain, rdtype=dns.rdatatype.A)
        ip = r[0].address
        if ipaddress.ip_address(ip):
            return ip
        else:
            return None

    def get_current_ip(self) -> str:
        ip = requests.get(self.ip_api_url).text
        if ipaddress.ip_address(ip):
            return ip
        else:
            return None

    def update_ddns(self):
        ip = None
        record = None
        count = 0
        while not all([ip, record]):
            ip = self.get_current_ip()
            record = self.query_ip_for_domain()
            if count >= 3:
                raise RuntimeError("Failed to check IP or DNS record!")
            else:
                count += 1
        if ip != record:
            api = NS1(apiKey=self.ns1_token)
            rec = api.loadRecord(self.domain, "A")
            rec.update(answers=[ip])
            self.send_message(f"Updating record with new IP:{ip} for domain:{self.domain}")
        else:
            print("Record already match,existing...")


if __name__ == '__main__':
    parser = ArgumentParser(prog='NS1 Updater', description='DDNS record updater for domain on NS1')
    parser.add_argument('-c', '--config', nargs='+')
    args = parser.parse_args()
    if args.config:
        json_file = args.config[0]
        with open(json_file, 'r') as conf_file:
            configs = json.load(conf_file)
        Updater = DDNSUpdater(domain=configs['domain'], ns1_token=configs['ns1_token'],
                              ip_api_url=configs['ip_api_url'], dns_server=configs['dns_server'],
                              pushover_user_key=configs['pushover_user_key'],
                              pushover_api_token=configs['pushover_api_token'])
        Updater.update_ddns()
    else:
        raise ValueError("No config file provided!")
