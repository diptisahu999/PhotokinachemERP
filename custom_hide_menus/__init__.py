# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

MENUS_TO_HIDE = [
    'project.menu_main_pm',
    'utm.menu_link_tracker_root',
    'survey.menu_surveys',
]


def post_init_hook(env):
    """Ensure target menus are deactivated and restricted upon module installation."""
    hidden_group = env.ref('custom_hide_menus.group_hidden_app_menus', raise_if_not_found=False)
    for xml_id in MENUS_TO_HIDE:
        menu = env.ref(xml_id, raise_if_not_found=False)
        if menu:
            vals = {'active': False}
            if hidden_group:
                vals['group_ids'] = [(6, 0, [hidden_group.id])]
            menu.sudo().write(vals)
            _logger.info("Hidden menu %s successfully.", xml_id)


def uninstall_hook(env):
    """Reactivate menus when module is uninstalled."""
    for xml_id in MENUS_TO_HIDE:
        menu = env.ref(xml_id, raise_if_not_found=False)
        if menu:
            menu.sudo().write({
                'active': True,
                'group_ids': [(5, 0, 0)],
            })
            _logger.info("Restored menu %s successfully.", xml_id)
