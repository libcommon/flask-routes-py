## -*- coding: UTF-8 -*-
## registry.py
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

try:
    from typing import Any, Callable, Type

    import flask
    from lc_registry import RegistryMetaclassMixin


    class RouteRegistryMixin(RegistryMetaclassMixin):
        """Mixin class to implement a route registry
        based on the RegistryMetaclassMixin class.
        """
        __slots__ = ()

        @classmethod
        def _add_class(cls, name: str, new_cls: Type[Any]) -> None:
            # Ensure ROUTE_MAP is defined and non-None on new_cls
            if hasattr(new_cls, "ROUTE_MAP") and new_cls.ROUTE_MAP:
                super()._add_class(name, new_cls)

        @classmethod
        def register_routes(cls, app: flask.Flask) -> None:
            """
            Args:
                app     => Flask app to register route(s) with
            Procedure:
                For each route handler class defined in the registry,
                attempt to register routes with provided Flask app using
                BaseRouteMixin.register_route.
            Preconditions:
                Each type defined in the registry must be child class of
                BaseRouteMixin. This requires:
                    1) A metaclass that extends this class: RouteRegistry(RouteRegistryMixin, type)
                    2) A base class with metaclass from step 1: BaseRoute(BaseRouteMixin, metaclass=RouteRegistry)
                        a) Could also use BaseRouteWithParserMixin
                    3) One or more route classes that extend class from step 2: IndexRoute(BaseRoute)
            Raises:
                N/A
            """
            # If registry defined
            if cls._REGISTRY:
                # For each route class
                for route_cls in cls._REGISTRY.values():
                    # Register route(s) with app
                    route_cls.register_route(app)

        @classmethod
        def register_routes_where(cls, app: flask.Flask, predicate: Callable[[Type[Any]], bool]) -> None:
            """Like register_routes, but with a predicate that must evaluate to True
            for any route to be registered.
            """
            # If registry defined
            if cls._REGISTRY:
                # For each route class
                for route_cls in cls._REGISTRY.values():
                    # If predicate passes
                    if predicate(route_cls):
                        # Register route(s) with app
                        route_cls.register_route(app)

