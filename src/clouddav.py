# -*- coding: iso-8859-1 -*-

# (c) 2010 Martin Wendt; see CloudDAV http://clouddav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

from future import standard_library
standard_library.install_aliases()
import logging
logging.getLogger().setLevel(logging.DEBUG)
from wsgidav.wsgidav_app import WsgiDAVApp, DEFAULT_CONFIG
from btfs.btfs_dav_provider import BTFSResourceProvider
from btfs.memcache_lock_storage import LockStorageMemcache
from btfs.google_domain_controller import GoogleDomainController

__version__ = "0.3.0a1"


def create_app():
    logging.debug("real_main")
    logger = logging.getLogger("wsgidav")
    logger.propagate = True
    logger.setLevel(logging.DEBUG)
    provider = BTFSResourceProvider()
    lockstorage = LockStorageMemcache()
    #domainController = GoogleDomainController()

    config = DEFAULT_CONFIG.copy()
    config.update({
        "provider_mapping": {"/": provider},
        "verbose": 3,
        "enable_loggers": ["http_authenticator"],
        "property_manager": False,
        "lock_manager": lockstorage,

        # Use Basic Authentication and don't fall back to Digest Authentication,
        # because our domain controller doesn't have no access to the user's 
        # passwords.
        "http_authenticator": {
            # None: dc.simple_dc.SimpleDomainController(user_mapping)
            #"domain_controller": None,
            "domain_controller": GoogleDomainController,
            "accept_basic": True,  # Allow basic authentication, True or False
            "accept_digest": False,  # Allow digest authentication, True or False
            "default_to_digest": False,  # True (default digest) or False (default basic)
            # Name of a header field that will be accepted as authorized user - set by App Engine for Google Login
            "trusted_auth_header": "USER_EMAIL",
        },
        "google_dc": {},
        "dir_browser": {
            "enable": True,          # Render HTML listing for GET requests on collections
            "response_trailer": "<a href='https://github.com/mar10/clouddav'>CloudDAV/%s</a> ${version} - ${time}" % __version__,
            "davmount": True,       # Send <dm:mount> response if request URL contains '?davmount'
            "msmount": True,        # Add an 'open as webfolder' link (requires Windows)
            },
        })
    return WsgiDAVApp(config)

# Using WSGI - https://cloud.google.com/appengine/docs/standard/python/migrate27#wsgi
app = create_app()

