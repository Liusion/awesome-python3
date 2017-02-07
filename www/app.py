#!/usr/bin/env python3
# -*- coding: utf-8 -*-



'''
async web application.
'''

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime
from config import configs
from aiohttp import web
#Environment应该指的是jinja2模板的环境配置，FileSystemLoader是文件系统加载器，用来加载模板路径
from jinja2 import Environment, FileSystemLoader
from handlers import cookie2user, COOKIE_NAME
import orm
from coroweb import add_routes, add_static
#这个函数功能是初始化jinja2模板，配置jinja2的环境
def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    #设置解析模板需要用到的环境变量
    options = dict(
        autoescape = kw.get('autoescape', True),#自动转义xml/html的特殊字符
        block_start_string = kw.get('block_start_string', '{%'),#设置代码块起始字符串，还有下面那句是结束字符串
        block_end_string = kw.get('block_end_string', '%}'),#意思就是{%和%}中间是python代码，而不是html
        variable_start_string = kw.get('variable_start_string', '{{'),#这两句分别设置了变量的起始和结束字符串
        variable_end_string = kw.get('variable_end_string', '}}'),#就是说{{和}}中间是变量
        auto_reload = kw.get('auto_reload', True)#当模板文件被修改后，下次请求加载该模板文件的时候会自动重新加载修改后的模板文件
    )
    path = kw.get('path', None)#从**kw中获取模板路径，如果没有传入这个参数则默认为None
    if path is None:#如果path为None，则将当前文件所在目录下的templates目录设置为模板文件的目录
        #下面这句代码其实是三个步骤，先取当前文件也就是app.py的绝对路径，然后取这个绝对路径的目录部分，最后在这个目录后面加上templates子目录
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    #loader=FileSystemLoader(path)指的是到哪个目录下加载模板文件，**options就是前面的options，用法和**kw类似
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)#过滤器在这儿的作用暂时还体现不出来，这四行注释掉也没事
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env#前面已经把jinja2的环境配置都赋值给env了，这里再把env存入app的dict中，这样app就知道要到哪儿去找模板，怎么解析模板。

#记录URL日志的middleware，当有http请求的时候，通过logging.info输出请求的信息，其中包括请求的方法和路径
@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return (yield from handler(request))
    return logger


#利用middleware在处理URL之前，把cookie解析出来，并将登录用户绑定到request对象上，这样，后续的URL处理函数就可以直接拿到登录用户
@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth







#当请求方法是POST的时候，有两种可能，Ajax的json和html的form(表单)，分别对应request.json()和request.post()，data_factory的主要作用就是把这些参数统一绑定在request.__data__上
@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (yield from handler(request))
    return parse_data

#这个middleware把返回值转换为web.Response对象再返回，以保证满足aiohttp的要求
@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info("Response handler...")
        # 调用handler来处理url请求,并返回响应结果
        r = yield from handler(request)
        # 若响应结果为StreamResponse,直接返回
        # StreamResponse是aiohttp定义response的基类,即所有响应类型都继承自该类
        # StreamResponse主要为流式数据而设计
        if isinstance(r, web.StreamResponse):
            return r
        # 若响应结果为字节流,则将其作为应答的body部分,并设置响应类型为流型
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = "application/octet-stream"
            return resp
        # 若响应结果为字符串
        if isinstance(r, str):
            # 判断响应结果是否为重定向.若是,则返回重定向的地址
            if r.startswith("redirect:"):
                return web.HTTPFound(r[9:])
            # 响应结果不是重定向,则以utf-8对字符串进行编码,作为body.设置相应的响应类型
            resp = web.Response(body = r.encode("utf-8"))
            resp.content_type = "text/html;charset=utf-8"
            return resp
        # 若响应结果为字典,则获取它的模板属性,此处为jinja2.env(见init_jinja2)
        if isinstance(r, dict):
            template = r.get("__template__")
            # 若不存在对应模板,则将字典调整为json格式返回,并设置响应类型为json
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode("utf-8"))
                resp.content_type = "application/json;charset=utf-8"
                return resp
            # 存在对应模板的,则将套用模板,用request handler的结果进行渲染
            else:
                r['__user__'] = request.__user__
                resp = web.Response(body=app["__templating__"].get_template(template).render(**r).encode("utf-8"))
                resp.content_type = "text/html;charset=utf-8"
                return resp
        # 若响应结果为整型的
        # 此时r为状态码,即404,500等
        if isinstance(r, int) and r >=100 and r<600:
            return web.Response
        # 若响应结果为元组,并且长度为2
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            # t为http状态码,m为错误描述
            # 判断t是否满足100~600的条件
            if isinstance(t, int) and t>= 100 and t < 600:
                # 返回状态码与错误描述
                return web.Response(t, str(m))
        # 默认以字符串形式返回响应结果,设置类型为普通文本
        resp = web.Response(body=str(r).encode("utf-8"))
        resp.content_type = "text/plain;charset=utf-8"
        return resp
    #上面6个if其实只用到了一个，准确的说只用到了半个。大家可以把用到的代码找出来，把没有用到的注释掉，如果程序能正常运行，那我觉得任务也就完成了
    #没用到的if语句块了解一下就好，等用到了再回过头来看，你就瞬间理解了。（这两条注释是我自己加的）
    return response

#这个时间过滤器的作用是返回日志创建的时间，用于显示在日志标题下面
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

#看到init记住就是初始化的意思，至于初始化什么玩意儿，我也说不太清楚
@asyncio.coroutine
def init(loop):
    #创建数据库连接池
    yield from orm.create_pool(loop=loop, **configs.db)
    #middlewares中间件预前处理request和response，包括打印日志、验证用户登陆、收集Request（请求）的数据
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])
    #初始化jinja2模板，并传入时间过滤器
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    #下面这两个函数在coroweb模块中
    add_routes(app, 'handlers')#handlers指的是handlers模块也就是handlers.py
    add_static(app)
    #监听127.0.0.1这个IP的9000端口的访问请求
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
