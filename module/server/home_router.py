# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import json
from fastapi import APIRouter, Body
from pathlib import Path

from module.config.utils import write_file
from module.image.rpc import ensure_image_server_ready, get_image_client, shutdown_image_server
from module.logger import logger
from module.server.api_logger import ApiLoggingRoute
from module.ocr.rpc import ensure_ocr_server_ready, get_ocr_client, shutdown_ocr_server
from module.server.main_manager import MainManager
from module.server.update_service import update_service
from module.server.i18n import I18n

home_app = APIRouter(
    prefix="/home",
    tags=["home"],
    route_class=ApiLoggingRoute,
)


@home_app.get('/test')
async def home_test():
    return {'message': 'test'}


#  gcc -Wall -pedantic -shared -fPIC -o group_work.so group_work.c -lwiringPi
@home_app.get('/home_menu')
async def home_menu():
    return {'Home': [], 'Updater': [], 'Tool': []}


@home_app.get('/image_server_info')
async def image_server_info():
    ensure_image_server_ready()
    return get_image_client(refresh=True).get_server_info()


@home_app.get('/ocr_server_info')
async def ocr_server_info():
    ensure_ocr_server_ready()
    return get_ocr_client(refresh=True).get_server_info()


@home_app.post('/notify_test')
async def notify_test(setting: str, title: str, content: str):
    from module.notify.notify import Notifier
    try:
        notifier = Notifier(setting, True)
        if notifier.push(title=title, content=content):
            del notifier
            return True
        else:
            del notifier
            return False
    except Exception as e:
        logger.exception(e)
        return str(e)


@home_app.get('/kill_server')
async def kill_server():
    shutdown_image_server()
    shutdown_ocr_server()
    MainManager.signal_kill_server = True
    return 'success'


@home_app.get('/update_info')
async def update_info():
    try:
        return await update_service.check()
    except Exception as e:
        logger.error(e)
        return dict(status='error', message=str(e), is_update=False, restart_required=False)


@home_app.post('/execute_update')
@home_app.get('/execute_update')  # Compatibility with the existing external frontend.
async def execute_update():
    return await update_service.install()


@home_app.get('/update_status')
async def update_status():
    return dict(result=update_service.last_result, installing=update_service.installing,
                restart_required=update_service.restart_required,
                dependencies_pending=update_service.dependencies_pending)


@home_app.put('/chinese_translate')
async def chinese_translate(data: dict = Body(...)):
    try:
        I18n.save_zh_cn(data)
    except Exception as e:
        logger.error(e)
    return True


@home_app.get('/additional_translate')
async def additional_translate() -> dict:
    try:
        data = I18n.load_additions()
        return data
    except Exception as e:
        logger.error(e)
    return {}


@home_app.get('/export_diagnostic')
async def export_diagnostic(config_name: str = ''):
    from module.server.diagnostic import build_diagnostic_zip
    try:
        zip_path = build_diagnostic_zip(config_name)
        return {'success': True, 'path': str(zip_path)}
    except Exception as e:
        logger.exception(e)
        return {'success': False, 'path': '', 'error': str(e)}
