import json
import warnings

import requests
from requests import RequestException
from requests.auth import HTTPProxyAuth

from elastalert.alerts import Alerter, DateTimeEncoder
from elastalert.util import EAException, elastalert_logger


class DingTalkAlerter(Alerter):
    """ Creates a DingTalk room message for each alert """
    required_options = frozenset(['dingtalk_access_token'])

    def __init__(self, rule):
        super(DingTalkAlerter, self).__init__(rule)
        self.dingtalk_access_token = self.rule.get('dingtalk_access_token', None)
        self.secret = self.rule.get('dingtalk_secret', '')                      #如果安全验证是签名模式需要带上 secretself.secret = self.rule.get('dingtalk_secret', '')                    self.dingtalk_webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=%s' % (self.dingtalk_access_token)
        self.dingtalk_msgtype = self.rule.get('dingtalk_msgtype', 'text')
        self.at_all = self.rule.get('dingtalk_at_all', False) 
        self.security_type = self.rule.get('dingtalk_security_type', 'keyword') #如果是sign需要传入 secret
        self.dingtalk_single_title = self.rule.get('dingtalk_single_title', 'elastalert')
        self.dingtalk_single_url = self.rule.get('dingtalk_single_url', '')
        self.dingtalk_btn_orientation = self.rule.get('dingtalk_btn_orientation', '')
        self.dingtalk_btns = self.rule.get('dingtalk_btns', [])
        self.dingtalk_proxy = self.rule.get('dingtalk_proxy', None)
        self.dingtalk_proxy_login = self.rule.get('dingtalk_proxy_login', None)
        self.dingtalk_proxy_password = self.rule.get('dingtalk_proxy_pass', None)
        
    def sign(self):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return "&timestamp={}&sign={}".format(timestamp, sign)

    def alert(self, matches):
        title = self.create_title(matches)
        body = self.create_alert_body(matches)

        proxies = {'https': self.dingtalk_proxy} if self.dingtalk_proxy else None
        auth = HTTPProxyAuth(self.dingtalk_proxy_login, self.dingtalk_proxy_password) if self.dingtalk_proxy_login else None
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json;charset=utf-8'
        }

        if self.dingtalk_msgtype == 'text':
            # text
            payload = {
                'msgtype': self.dingtalk_msgtype,
                'text': {
                    'content': body
                }
            }
        if self.dingtalk_msgtype == 'markdown':
            # markdown
            payload = {
                'msgtype': self.dingtalk_msgtype,
                'markdown': {
                    'title': title,
                    'text': body
                }
            }
        if self.dingtalk_msgtype == 'single_action_card':
            # singleActionCard
            payload = {
                'msgtype': 'actionCard',
                'actionCard': {
                    'title': title,
                    'text': body,
                    'singleTitle': self.dingtalk_single_title,
                    'singleURL': self.dingtalk_single_url
                }
            }
        if self.dingtalk_msgtype == 'action_card':
            # actionCard
            payload = {
                'msgtype': 'actionCard',
                'actionCard': {
                    'title': title,
                    'text': body
                }
            }
            if self.dingtalk_btn_orientation != '':
                payload['actionCard']['btnOrientation'] = self.dingtalk_btn_orientation
            if self.dingtalk_btns:
                payload['actionCard']['btns'] = self.dingtalk_btns

        if self.security_type == "sign":
            webhook_url = '%s%s' %(webhook_url , self.sign())
        try:
            response = requests.post(self.dingtalk_webhook_url, data=json.dumps(payload,
                                     cls=DateTimeEncoder), headers=headers, proxies=proxies, auth=auth)
            warnings.resetwarnings()
            response.raise_for_status()
        except RequestException as e:
            raise EAException("Error posting to dingtalk: %s" % e)

        elastalert_logger.info("Trigger sent to dingtalk")

    def get_info(self):
        return {
            "type": "dingtalk",
            "dingtalk_webhook_url": self.dingtalk_webhook_url
        }
