## -*- coding: UTF-8 -*-
## route.py
##
## Copyright (c) 2020 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.
# pylint: disable=W0613

import logging
import os
from typing import Any, ClassVar, Dict, Optional, Tuple, Union

import flask
from werkzeug.local import LocalProxy as WerkzeugLocalProxy
from werkzeug.wrappers import Response as WerkzeugResponse


__author__ = "libcommon"
logger = logging.getLogger(__name__)    # pylint: disable=invalid-name


RouteMap = Dict[str, Dict[str, Any]]
RouteResponseData = Union[WerkzeugResponse, Dict[str, Any], str]
RouteResponse = Union[Tuple[RouteResponseData, int], RouteResponseData]


class BaseRouteMixin:
    """Mixin for Flask routes intended to be replacement for
    using the typical @app.route decorator, and to be used with
    `RouteRegistryMixin` (though not required). Supports GET, POST, PUT, and DELETE
    HTTP methods out of the box, any other methods could be supported by a subclass.
    All handlers are classmethods, so each route class acts like a singleton
    (with no instance-level state).
    """
    __slots__ = ()

    # key-value pairs map to arguments for the flask.Flask.add_url_rule
    # see: https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.add_url_rule
    ROUTE_MAP: ClassVar[Optional[RouteMap]] = None

    @classmethod
    def register_route(cls, app: flask.Flask) -> None:
        """
        Args:
            app     => Flask app to register route(s) with
        Procedure:
            Register route(s) defined in cls.ROUTE_MAP with provided Flask app.
        Preconditions:
            N/A
        Raises:
            This function does not raise an exception, because the failure to register
            one route should not necessarily preclude registering other routes. Instead,
            it logs a WARNING for each route that fails.
        """
        # If ROUTE_MAP defined
        if cls.ROUTE_MAP:
            # For each route defined in ROUTE_MAP
            for route, route_options in cls.ROUTE_MAP.items():
                try:
                    # Ensure "view_func" key isn't defined in route_options
                    # Would conflict with setting view_func=cls.handle_request
                    if "view_func" in route_options:
                        raise KeyError("route options cannot contain \"view_func\" key")
                    # Add route with options to app, using cls.handle_request as route handler ("view_func")
                    app.add_url_rule(route, view_func=cls.handle_request, **route_options)
                except Exception as exc:
                    logger.warning("Failed to register handler for route {} ({})".format(route, exc))

    @classmethod
    def handle_request(cls, **route_kwargs) -> RouteResponse:
        """
        Args:
            route_kwargs    => arguments from variable rules
                               (see: https://flask.palletsprojects.com/en/1.1.x/quickstart/#variable-rules)
        Returns:
            Response from appropriate HTTP method handler.
        Preconditions:
            N/A
        Raises:
            TODO
        """
        # Get current app, request, and session
        app = flask.current_app
        request = flask.request
        request_method = request.method.lower()
        session = flask.session

        # If class doesn't have handler defined for HTTP method, return 405 response
        # This protects against a situation where an HTTP method is enabled in cls.ROUTE_MAP
        # but no associated handler is implemented.
        # see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/405
        if not hasattr(cls, request_method):
            flask.abort(405)

        # Trigger handler for method
        return getattr(cls, request_method)(app, request, session, route_kwargs)

    @classmethod
    def get(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle GET requests to route(s)."""
        flask.abort(405)

    @classmethod
    def post(cls,
             app: WerkzeugLocalProxy,
             request: WerkzeugLocalProxy,
             session: WerkzeugLocalProxy,
             route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle POST requests to route(s)."""
        flask.abort(405)

    @classmethod
    def put(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle PUT requests to route(s)."""
        flask.abort(405)

    @classmethod
    def delete(cls,
               app: WerkzeugLocalProxy,
               request: WerkzeugLocalProxy,
               session: WerkzeugLocalProxy,
               route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle DELETE requests to route(s)."""
        flask.abort(405)


try:
    from lc_flask_reqparser import RequestParser


    class BaseRouteWithParserMixin(BaseRouteMixin):
        """Like `BaseRouteMixin`, but supports defining a
        `RequestParser` to parse GET, POST, or PUT parameters.
        """
        __slots__ = ()

        @classmethod
        def gen_request_parser(cls) -> Optional[RequestParser]:
            """
            Args:
                N/A
            Returns:
                Parser for URL parameters (GET) or request body (POST/PUT). Default
                implementation returns None.
            Preconditions:
                N/A
            Raises:
                N/A
            """
            return None

        @classmethod
        def handle_request(cls, **route_kwargs) -> RouteResponse:
            # Get current request and HTTP method
            request = flask.request
            request_method = request.method

            # Generate request parser
            parser = cls.gen_request_parser()
            # If request parser defined and HTTP method is GET, POST, or PUT
            if parser and request_method in {"GET", "POST", "PUT"}:
                try:
                    # Try to parse known request arguments
                    args, _ = parser.parse_args()
                except TypeError:
                    # Indicates invalid mimetype for POST/PUT request
                    # return 415 response ("Unsupported Media Type")
                    # see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/415
                    flask.abort(415)
                except RuntimeError as exc:
                    # If error message indicates failed to parse
                    # request arguments, return 400 response ("Bad Request")
                    # see: RequestParser.error
                    if (exc.args and
                        isinstance(exc.args[0], str) and
                        exc.args[0].startswith("Failed to parse provided arguments")):
                        flask.abort(400)
                    # Otherwise, indicates outside of request context
                    # and should raise original exception
                    else:
                        raise

                # Merge parsed request arguments with route_kwargs
                # NOTE: request arguments will override route variable rules
                route_kwargs.update(dict(args._get_kwargs()))

            # Trigger handler from BaseRouteMixin with updated route_kwargs
            return super().handle_request(**route_kwargs)

except (ImportError, ModuleNotFoundError):
    pass
