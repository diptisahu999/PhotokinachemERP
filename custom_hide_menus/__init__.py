# -*- coding: utf-8 -*-
import logging
from . import models

_logger = logging.getLogger(__name__)

MENUS_TO_HIDE = [
    'project.menu_main_pm',
    'utm.menu_link_tracker_root',
    'survey.menu_surveys',
]


def post_init_hook(env):
    """Ensure target menus are deactivated or restricted upon module installation."""
    hidden_group = env.ref('custom_hide_menus.group_hidden_app_menus', raise_if_not_found=False)
    apps_group = env.ref('custom_hide_menus.group_apps_access', raise_if_not_found=False)

    for xml_id in MENUS_TO_HIDE:
        menu = env.ref(xml_id, raise_if_not_found=False)
        if menu:
            vals = {'active': False}
            if hidden_group:
                vals['group_ids'] = [(6, 0, [hidden_group.id])]
            menu.sudo().write(vals)
            _logger.info("Hidden menu %s successfully.", xml_id)

    # Restrict Apps menu strictly to group_apps_access
    for apps_xml_id in ['base.menu_management', 'base.menu_apps']:
        menu = env.ref(apps_xml_id, raise_if_not_found=False)
        if menu and apps_group:
            menu.sudo().write({
                'group_ids': [(6, 0, [apps_group.id])]
            })
            _logger.info("Restricted %s to Apps Module Access group.", apps_xml_id)


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

    for apps_xml_id in ['base.menu_management', 'base.menu_apps']:
        menu = env.ref(apps_xml_id, raise_if_not_found=False)
        if menu:
            menu.sudo().write({
                'group_ids': [(5, 0, 0)],
            })
            _logger.info("Restored %s permissions.", apps_xml_id)