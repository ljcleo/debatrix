from .classes import ArenaInterface, Manager, Model, PanelInterface


class ProcessHub:
    def __init__(
        self,
        *,
        debug: bool,
        log_info: bool,
        pre_arena_callback,
        in_arena_callback,
        post_arena_callback,
        pre_panel_callback,
        in_panel_callback,
        post_panel_callback
    ) -> None:
        self._model = Model(debug=debug, log_info=log_info)

        self._arena_interface = ArenaInterface(
            debug=debug,
            log_info=log_info,
            callback=in_arena_callback,
        )

        self._panel_interface = PanelInterface(
            debug=debug,
            log_info=log_info,
            callback=in_panel_callback,
        )

        self._manager = Manager(
            debug=debug,
            log_info=log_info,
            pre_arena_callback=pre_arena_callback,
            post_arena_callback=post_arena_callback,
            pre_panel_callback=pre_panel_callback,
            post_panel_callback=post_panel_callback,
        )

    @property
    def model(self) -> Model:
        return self._model

    @property
    def arena_interface(self) -> ArenaInterface:
        return self._arena_interface

    @property
    def panel_interface(self) -> PanelInterface:
        return self._panel_interface

    @property
    def manager(self) -> Manager:
        return self._manager
