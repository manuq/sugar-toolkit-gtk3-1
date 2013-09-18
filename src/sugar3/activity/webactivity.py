# Copyright (C) 2013 Daniel Narvaez
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import json
import os

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import WebKit
from gi.repository import Gtk
from gi.repository import GdkX11
assert GdkX11

from gi.repository import SugarExt
from sugar3.activity import activity


class WebActivity(Gtk.Window):
    def __init__(self, handle):
        Gtk.Window.__init__(self)

        self._activity_id = handle.activity_id
        self._object_id = handle.object_id
        self._bundle_id = os.environ["SUGAR_BUNDLE_ID"]
        self._bundle_path = os.environ["SUGAR_BUNDLE_PATH"]
        self._inspector_visible = False

        self.set_decorated(False)
        self.maximize()

        self.connect("key-press-event", self._key_press_event_cb)
        self.connect('realize', self._realize_cb)
        self.connect('destroy', self._destroy_cb)

        self._web_view = WebKit.WebView()
        self._web_view.connect("notify::load-status", self._loading_changed_cb)
        self._web_view.connect("resource-request-starting",
                               self._resource_request_starting_cb)

        self.add(self._web_view)
        self._web_view.show()

        settings = self._web_view.get_settings()
        settings.set_property("enable-developer-extras", True)

        # FIXME this is a security hole
        settings.set_property('enable-file-access-from-file-uris', True)

        self._web_view.load_uri("activity://%s/index.html" % self._bundle_id)
        self.set_title(activity.get_bundle_name())

    def run_main_loop(self):
        Gtk.main()

    def _realize_cb(self, window):
        xid = window.get_window().get_xid()
        SugarExt.wm_set_bundle_id(xid, self._bundle_id)
        SugarExt.wm_set_activity_id(xid, str(self._activity_id))

    def _destroy_cb(self, window):
        self.destroy()
        Gtk.main_quit()

    def _resource_request_starting_cb(self, webview, web_frame, web_resource,
                                      request, response):
        uri = web_resource.get_uri()
        if uri.startswith('activity://'):
            prefix = "activity://%s" % self._bundle_id
            new_prefix = "file://%s" % activity.get_bundle_path()
            new_uri = new_prefix + uri[len(prefix):]

            request.set_uri(new_uri)

    def _loading_changed_cb(self, web_view, load_status):
        status = web_view.get_load_status()

        if status == WebKit.LoadStatus.FINISHED:
            key = os.environ["SUGAR_APISOCKET_KEY"]
            port = os.environ["SUGAR_APISOCKET_PORT"]

            env_json = json.dumps({"apiSocketKey": key,
                                   "apiSocketPort": port,
                                   "activityId": self._activity_id,
                                   "bundleId": self._bundle_id,
                                   "objectId": self._object_id,
                                   "activityName": activity.get_bundle_name()})

            script = """
                     var environment = %s;

                     if (window.sugar === undefined) {
                         window.sugar = {};
                     }

                     window.sugar.environment = environment;

                     if (window.sugar.onEnvironmentSet)
                         window.sugar.onEnvironmentSet();
                    """ % env_json

            self._web_view.execute_script(script)

    def _key_press_event_cb(self, window, event):
        key_name = Gdk.keyval_name(event.keyval)

        if event.get_state() & Gdk.ModifierType.CONTROL_MASK and \
           event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            if key_name == "I":
                inspector = self._web_view.get_inspector()
                if self._inspector_visible:
                    inspector.close()
                    self._inspector_visible = False
                else:
                    inspector.show()
                    self._inspector_visible = True

                return True

    def _app_scheme_cb(self, request, user_data):
        path = os.path.join(self._bundle_path,
                            os.path.relpath(request.get_path(), "/"))

        request.finish(Gio.File.new_for_path(path).read(None),
                       -1, Gio.content_type_guess(path, None)[0])
