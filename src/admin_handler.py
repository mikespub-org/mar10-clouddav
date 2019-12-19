# -*- coding: iso-8859-1 -*-

# (c) 2010 Martin Wendt; see CloudDAV http://clouddav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

from builtins import str
from flask import Flask, render_template, request
from btfs import db
from btfs.db import stats
from btfs.auth import users, AuthorizedUser
from btfs.cache import memcache3
from btfs.model import Path, Dir, File, Chunk
from pprint import pformat
import os
import logging


def db_get_stats(model, limit=1000):
    stats = {
        'kind': model.kind(),
        'properties': model.properties(),
        'count': model.get_count(limit)
    }
    for name in stats['properties']:
        proptype = type(stats['properties'][name]).__name__
        stats['properties'][name] = proptype.replace('google.appengine.ext.', '')
    if stats['count'] == limit:
        stats['count'] = str(limit) + '+'
    return stats


def find_orphans(limit=1000):
    dir_list = Dir.list_all(1000)
    dir_keys = {}
    for item in dir_list:
        dir_keys[item.key()] = item
    output = "Orphan Dirs:\n"
    dir_orphans = []
    for item in dir_list:
        if not item.parent_path:
            if item.path != '/':
                output += 'No Parent Path: %s\n' % item.path
                dir_orphans.append(item.key())
            continue
        try:
            key = item.parent_path
        except Exception as e:
            output += 'Invalid Reference: %s\n' % item.path
            dir_orphans.append(item.key())
            continue
        if key not in dir_keys:
            output += 'Unknown Parent: %s\n' % item.path
            dir_orphans.append(item.key())
    del(dir_list)
    file_list = File.list_all(1000)
    output += "Orphan Files:\n"
    file_keys = {}
    file_orphans = []
    for item in file_list:
        file_keys[item.key()] = item
        try:
            key = item.parent_path
        except Exception as e:
            output += 'Invalid Reference: %s\n' % item.path
            file_orphans.append(item.key())
            continue
        if key not in dir_keys:
            output += 'Unknown Parent: %s\n' % item.path
            file_orphans.append(item.key())
            continue
        if key in dir_orphans:
            output += 'Orphan Dir: %s\n' % item.path
            file_orphans.append(item.key())
            continue
        file_keys[item.key()] = item
    del(file_list)
    chunk_list = Chunk.list_all(1000, projection=['offset'])
    output += "Orphan Chunks:\n"
    #chunk_keys = {}
    chunk_orphans = []
    for item in chunk_list:
        try:
            key = item.key().parent
        except Exception as e:
            output += 'Invalid Reference: %s\n' % item.key()
            chunk_orphans.append(item.key())
            continue
        if key not in file_keys:
            output += 'Unknown File: %s %s\n' % (item.key().parent, item.offset)
            chunk_orphans.append(item.key())
            continue
        if key in file_orphans:
            output += 'Orphan File: %s %s\n' % (item.key().parent, item.offset)
            chunk_orphans.append(item.key())
            continue
        #chunk_keys[item.key()] = item
    del(chunk_list)
    # TODO: resize files & dirs based on chunk_keys?
    return output, dir_orphans, file_orphans, chunk_orphans


app = Flask(__name__)
app.debug = True


@app.route('/_admin')
def admin_view():
    if not users.is_current_user_admin():
        output = "You need to login as administrator <a href='%s'>Login</a>" % users.create_login_url(request.url)
        return output
    qs = request.query_string
    if not isinstance(qs, str):
        qs = qs.decode('utf-8')
    logging.warning("AdminHandler.get: %s" % qs)
    # Handle admin commands
    if qs == "run_tests":
        from btfs.test import test
        test()
        output = "Tests run! <a href='?'>Back</a>"
        return output
    elif qs == "clear_cache":
        logging.warning("clear_cache: memcache3.reset()")
        memcache3.reset()
        output = "Memcache deleted! <a href='?'>Back</a>"
        return output
    elif qs == "clear_datastore":
        logging.warning("clear_datastore: fs.rmtree('/')")
        from btfs import fs
        # cannot use rmtree("/"), because it prohibits '/'
        try:
            fs.rmtree("/")
        except Exception as e:
            logging.warning(e)
#        fs.getdir("/").delete(recursive=True)
        memcache3.reset()
        fs.initfs()
        output = "Removed '/'. <a href='?'>Back</a>"
        return output
    elif qs == "check_orphans":
        output = "Checking orphans. <a href='?'>Back</a><pre>"
        result, dir_orphans, file_orphans, chunk_orphans = find_orphans()
        output += result
        output += "</pre>Total orphans: %s dirs, %s files, %s chunks" % (len(dir_orphans), len(file_orphans), len(chunk_orphans))
        if len(dir_orphans) + len(file_orphans) + len(chunk_orphans) > 0:
            output += " - <a href='?delete_orphans'>Delete orphans?</a>"
        return output
    elif qs == "delete_orphans":
        output, dir_orphans, file_orphans, chunk_orphans = find_orphans()
        total = 0
        if len(dir_orphans) > 0:
            total += len(dir_orphans)
            db.delete(dir_orphans)
        if len(file_orphans) > 0:
            total += len(file_orphans)
            db.delete(file_orphans)
        if len(chunk_orphans) > 0:
            total += len(chunk_orphans)
            db.delete(chunk_orphans)
        output = "Deleted %s orphans. <a href='?'>Back</a>" % total
        return output
    elif qs != "":
        raise NotImplementedError("Invalid command: %s" % qs)
    # Show admin page
    user = users.get_current_user()
    if user:
        url = users.create_logout_url(request.url)
        url_linktext = 'Logout'
    else:
        url = users.create_login_url(request.url)
        url_linktext = 'Login'
    env = []
    for k, v in list(os.environ.items()):
        env.append("%s: '%s'" % (k, v))
    datastore_stats = {}
    #datastore_stats['Stats'] = stats.GlobalStat.list_all(1)
    datastore_stats['Stats'] = []
    #for stat in stats.KindPropertyNamePropertyTypeStat.list_all():
    #    datastore_stats['Stats'].append(stat)
    datastore_stats['Path'] = db_get_stats(Path)
    datastore_stats['Dir'] = db_get_stats(Dir)
    datastore_stats['File'] = db_get_stats(File)
    datastore_stats['Chunk'] = db_get_stats(Chunk)
    datastore_stats['User'] = db_get_stats(AuthorizedUser)
    paths = []
    for item in Path.list_all(10):
        info = dict(item._entity)
        info['__key__'] = item.key()
        paths.append(info)
    chunks = []
    for item in Chunk.list_all(10):
        info = dict(item._entity)
        if len(info['data']) > 100:
            info['data'] = '%s... (%s bytes)' % (info['data'][:100], len(info['data']))
        info['__key__'] = item.key()
        chunks.append(info)
    userlist = []
    for item in AuthorizedUser.list_all(10):
        info = dict(item._entity)
        info['__key__'] = item.key()
        userlist.append(info)
    template_values = {
        "nickname": user.nickname(),
        "url": url,
        "url_linktext": url_linktext,
        "memcache_stats": pformat(memcache3.get_stats()),
        "datastore_stats": pformat(datastore_stats),
        "path_samples": pformat(paths),
        "chunk_samples": pformat(chunks),
        "user_samples": pformat(userlist),
        "environment_dump": "\n".join(env),
        }

    return render_template('admin.html', **template_values)
 
