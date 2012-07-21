#! /usr/bin/env python

# PyProxyPass: http://github.com/TermiT/PyProxyPass/
# Author: Gennadiy Potapov <drtermit@gmail.com>
# License: MIT

import SocketServer
import SimpleHTTPServer
import urllib2
from os import path, chdir
from urlparse import urlparse, urljoin

SCRIPT_PATH = path.dirname(path.realpath(__file__))

PORT = 8880
SERVE_PATH = path.join(SCRIPT_PATH, '../dist/')
FOLLOW_REDIRECT = True
PROXY_RULES = {
    '/google/' : 'http://google.com/',
}

class Proxy(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def __do_proxy(self):
        prefix = None
        for key in PROXY_RULES.iterkeys():
            if self.path.startswith(key):
                prefix = key
                break

        if prefix:
            # Strip off the prefix.
            url = urljoin(PROXY_RULES[prefix], self.path.partition(prefix)[2])
            hostname = urlparse(PROXY_RULES[prefix]).netloc

            body = None
            if self.headers.getheader('content-length') is not None:
                content_len = int(self.headers.getheader('content-length'))
                body = self.rfile.read(content_len)

            # set new headers
            new_headers = {}
            for item in self.headers.items():
                new_headers[item[0]] = item[1]
            new_headers['host'] = hostname

            # accept-encoding cosing
            try:
                del new_headers['accept-encoding']
            except KeyError:
                pass

            try:
                response = self.__do_request(url, body, new_headers)
                self.send_response(response.getcode())
                headers = response.info().dict
                skip_headers = ['date', 'server', 'transfer-encoding']
                for header_key in headers:
                    if header_key in skip_headers:
                        continue
                    self.send_header('-'.join((ck.capitalize() for ck in header_key.split('-'))), headers[header_key])
                self.end_headers()
                self.copyfile(response, self.wfile)
            except IOError, e:
                print "ERROR: ", e
        else:
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def __do_request(self, url, body, headers):
        req = urllib2.Request(url, body, headers)
        try:
            response = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if FOLLOW_REDIRECT and hasattr(e, 'code') and (e.code == 301 or e.code == 302):
                headers['host'] = urlparse(e.url).netloc
                return self.__do_request(e.url, body, headers)
            else:
                response = e
        return response

    def do_GET(self):
        self.__do_proxy()

    def do_HEAD(self):
        self.__do_proxy()

    def do_POST(self):
        self.__do_proxy()

chdir(SERVE_PATH)
SocketServer.ThreadingTCPServer.allow_reuse_address = True
httpd = SocketServer.ThreadingTCPServer(('', PORT), Proxy)
print "Starting proxy server at ", PORT, "...", "\n", "Ready"
httpd.serve_forever()
