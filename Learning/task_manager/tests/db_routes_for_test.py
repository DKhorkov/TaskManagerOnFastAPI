import logging

from fastapi import Request, Form, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_302_FOUND
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.templating import Jinja2Templates

from Learning.task_manager.database.database import get_async_session
from Learning.task_manager.config import Settings
from Learning.task_manager.users import get_current_user
from .session_for_test import TestTask, TestUser


logging.basicConfig(format='[%(asctime)s: %(levelname)s] %(message)s', filename="../log/test_logs", filemode='a')
logger = logging.getLogger("")
logger.setLevel(level=logging.DEBUG)

test_db_router = APIRouter()
templates = Jinja2Templates(directory='./templates/task_manager')  # Указываем, где будут лежать наши HTML шаблоны


@test_db_router.get("/test_tasks", name='tasks', response_class=HTMLResponse)
async def tasks(request: Request, session: AsyncSession = Depends(get_async_session),
                current_user: TestUser = Depends(get_current_user)):
    """
        Функция получает все созданные заявки и возвращает отрисованный HTML шаблон с данными заявками.

        :param request: Обязательный параметр запроса для нашей странички по аналогии с Django
        :param current_user: Текущий пользователь, под которого будут выведены созданные им заявки
        :param session: Объект сессии из SQLAlchemy. В нее передаются зависимости нашей базы данных.

        :return: Отрисованный HTML, созданный с помощью шаблонизатора Jinja2Templates
    """
    try:
        async with session as async_session:
            all_tasks = await async_session.execute(select(TestTask).filter(TestTask.user_id == current_user.id))
            all_tasks = all_tasks.scalars()  # Переводим в скалярный вид для доступа к таскам и отрисовки в HTML

        return templates.TemplateResponse(
            name="tasks.html",  # Путь до шаблона
            context={'request': request,  # Context - данные, которые мы передаем в шаблон
                     'app_name': Settings().app_name,
                     'tasks_list': all_tasks},
            status_code=200,
        )

    except Exception as e:
        logger.debug(e)
        raise HTTPException(status_code=500, detail="Something went wrong")


@test_db_router.post("/test_add", name='add', response_class=RedirectResponse)
async def add(title: str = Form(..., description="Укажите описание заявки"),
              session: AsyncSession = Depends(get_async_session),
              current_user: TestUser = Depends(get_current_user)):
    """
        Функция получает название новой заявки, создает экземпляр модели заявки и сохраняет заявку в базу данных.
        Переадресовывает на домашнюю страницу.

        :param title: Обязательный параметр формы, для создания новой заявки
        :param session: Объект сессии из SQLAlchemy. В нее передаются зависимости нашей базы данных.
        :param current_user: Текущий пользователь, под которого будут выведены созданные им заявки

        :return: Отрисованный HTML, созданный с помощью шаблонизатора Jinja2Templates
    """
    try:
        new_task = TestTask(title=title, user_id=current_user.id)
        async with session as async_session:
            async_session.add(new_task)
            await async_session.commit()

        home_url = test_db_router.url_path_for('tasks')
        return RedirectResponse(url=home_url, status_code=HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.debug(e)
        raise HTTPException(status_code=500, detail="Something went wrong")


@test_db_router.get('/test_update/{task_id}', name='update', response_class=RedirectResponse)
async def update(task_id: int, session: AsyncSession = Depends(get_async_session),
                 current_user: TestUser = Depends(get_current_user)):
    """
        Функция получает идентификационный номер заявки, находит ее и меняет статус на противоположный от того,
        который был.

        :param task_id: Идентификационный номер заявки для редактирования
        :param session: Объект сессии из SQLAlchemy. В нее передаются зависимости нашей базы данных.
        :param current_user: Текущий пользователь, под которого будут выведены созданные им заявки

        :return: Отрисованный HTML, созданный с помощью шаблонизатора Jinja2Templates
    """
    try:
        async with session as async_session:
            task_to_update = await async_session.execute(select(TestTask).filter(TestTask.id == task_id))
            task_to_update = task_to_update.scalar()

            # Проверка, что таска принадлежит текущему пользователю:
            if not task_to_update.user_id == current_user.id:
                logger.debug(f'User with id={current_user.id} tried to update task with id={task_id}, which does not '
                             f'belongs to him!')
                raise HTTPException(status_code=404, detail="You are not allowed to change other user's tasks!")

            task_to_update.is_complete = not task_to_update.is_complete
            await async_session.commit()

        url = test_db_router.url_path_for('tasks')

        return RedirectResponse(url=url, status_code=HTTP_302_FOUND)

    except Exception as e:
        logger.debug(e)
        raise HTTPException(status_code=500, detail="Something went wrong")


@test_db_router.get('/test_delete/{task_id}', name='delete', response_class=RedirectResponse)
async def delete(task_id: int, session: AsyncSession = Depends(get_async_session),
                 current_user: TestUser = Depends(get_current_user)):
    """
        Функция получает идентификационный номер заявки, находит ее и удаляет.

        :param task_id: Идентификационный номер заявки для редактирования
        :param session: Объект сессии из SQLAlchemy. В нее передаются зависимости нашей базы данных.
        :param current_user: Текущий пользователь, под которого будут выведены созданные им заявки

        :return: Отрисованный HTML, созданный с помощью шаблонизатора Jinja2Templates
    """
    try:
        async with session as async_session:
            task_to_delete = await async_session.execute(select(TestTask).filter_by(id=task_id))
            task_to_delete = task_to_delete.scalar()

            # Проверка, что таска принадлежит текущему пользователю:
            if not task_to_delete.user_id == current_user.id:
                logger.debug(f'User with id={current_user.id} tried to delete task with id={task_id}, which does not '
                             f'belongs to him!')
                raise HTTPException(status_code=404, detail="You are not allowed to delete other user's tasks!")

            await async_session.delete(task_to_delete)
            await async_session.commit()

        url = test_db_router.url_path_for('tasks')
        return RedirectResponse(url=url, status_code=HTTP_302_FOUND)

    except Exception as e:
        logger.debug(e)
        raise HTTPException(status_code=500, detail="Something went wrong")
