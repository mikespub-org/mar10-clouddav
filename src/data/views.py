#
# Copyright (c) 2019-2020 Mike's Pub, see https://github.com/mikespub-org
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

import logging
import time

from flask import Flask, render_template, request

# from btfs import sessions
from . import db
from . import api


BASE_URL = "/data"


def create_app(debug=True, base_url="/data", templates="../templates"):
    """Create main Flask app if this module is the entrypoint, e.g. python3 -m data.views"""
    app = Flask(__name__)
    app.debug = debug
    app.template_folder = templates
    configure_app(app, base_url=base_url)
    return app


# app = create_app()


def configure_app(app, base_url="/data", authorize_wrap=None):
    """Configure existing Flask app with datastore view functions, template filters and global functions"""
    global BASE_URL
    BASE_URL = base_url
    if authorize_wrap:
        app.add_url_rule(base_url + "/", view_func=authorize_wrap(home_view))
        app.add_url_rule(
            base_url + "/<string:name>/", view_func=authorize_wrap(list_view)
        )
        app.add_url_rule(
            base_url + "/<string:parent>/<path:item>",
            view_func=authorize_wrap(item_view),
        )
    else:
        app.add_url_rule(base_url + "/", view_func=home_view)
        app.add_url_rule(base_url + "/<string:name>/", view_func=list_view)
        app.add_url_rule(base_url + "/<string:parent>/<path:item>", view_func=item_view)
    app.add_template_filter(is_item)
    app.add_template_filter(item_link)
    app.add_template_filter(show_link)
    app.add_template_filter(show_date)
    app.add_template_global(get_pager)
    # app.add_template_global(get_lists)
    # app.add_template_global(get_stats)


# @app.template_filter()
def is_item(key):
    if "Key" in key.__class__.__name__:
        return True
    return False


# @app.template_filter()
def item_link(key):
    if not is_item(key):
        return key
    return api.item_to_path(key)


# @app.template_filter()
def show_link(key):
    return '<a href="%s/%s">%s</a>' % (base_url, item_link(key), key.id_or_name)


# @app.template_filter()
def show_date(timestamp, fmt="%Y-%m-%d %H:%M:%S"):
    if not timestamp:
        return
    if isinstance(timestamp, (int, float)):
        return time.strftime(fmt, time.gmtime(timestamp))
    return timestamp.strftime(fmt)


# @app.template_global()
def get_pager(count=None, page=1, size=None):
    if size is None:
        size = api.PAGE_SIZE
    if count is not None and count <= size:
        return
    first_url = None
    prev_url = None
    next_url = None
    last_url = None
    url = request.url
    if "page=" in url:
        page_url = url.replace("page=%s" % page, "page=")
        if "&page=" in page_url:
            base_url = page_url.replace("&page=", "")
        else:
            base_url = page_url.replace("?page=", "")
    elif "?" in url:
        base_url = url
        page_url = url + "&page="
    else:
        base_url = url
        page_url = url + "?page="
    if page > 1:
        first_url = base_url
    if page > 2:
        prev_url = page_url + str(page - 1)
    elif page > 1:
        prev_url = base_url
    if count is None:
        next_url = page_url + str(page + 1)
        return (first_url, prev_url, next_url, last_url)
    max_page = int(count / size) + 1
    if page < max_page:
        next_url = page_url + str(page + 1)
        last_url = page_url + str(max_page)
    return (first_url, prev_url, next_url, last_url)


# @app.route("/data/")
# @sessions.flask_authorize("admin")
def home_view(name=None):
    # when dealing with Others coming from list_view
    kinds_list = api.home_get(name)
    reset = request.args.get("reset", False)
    stats = api.get_stats(reset)
    return render_template(
        "data_home.html", base_url=BASE_URL, lists=kinds_list, name=name, stats=stats,
    )


# @app.route("/data/<string:name>/")
# @sessions.flask_authorize("admin")
def list_view(name):
    kinds_list = api.get_models()
    if name not in api.KNOWN_MODELS:
        kinds_list = api.get_lists()
        if name not in kinds_list or name == "Others":
            return home_view(name)
    page = int(request.args.get("page", 1))
    sort = request.args.get("sort", None)
    fields = request.args.get("fields", None)
    rows = api.list_get(name, page, sort, fields)
    columns = []
    if len(rows) > 0:
        columns = sorted(rows[0].keys())
    count = api.get_list_count(name)
    return render_template(
        "data_list.html",
        base_url=BASE_URL,
        lists=kinds_list,
        name=name,
        sort=sort,
        page=page,
        count=count,
        columns=columns,
        rows=rows,
    )


# @app.route("/data/<string:parent>/<path:item>")
# @sessions.flask_authorize("admin")
def item_view(parent, item):
    kinds_list = api.get_models()
    if parent not in api.KNOWN_MODELS:
        kinds_list = api.get_lists()
        if parent not in kinds_list or parent == "Others":
            return home_view(parent)
    fields = request.args.get("fields", None)
    children = request.args.get("children", False)
    info = api.item_get(parent, item, fields=fields, children=children)
    return render_template(
        "data_item.html", base_url=BASE_URL, lists=kinds_list, name=parent, info=info,
    )


if __name__ == "__main__":
    # python3 -m data.views
    app = create_app()
    app.run(host="0.0.0.0", port=8080, use_reloader=False)
