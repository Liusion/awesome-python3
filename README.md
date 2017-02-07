# 代码结构
    www
		- static:存放静态资源
		- templates:存放模板文件
		- app.py: HTTP服务器以及处理HTTP请求；拦截器、jinja2模板、URL处理函数注册等
		- orm.py: ORM框架
		- coroweb.py: 封装aiohttp，即写个装饰器更好的从Request对象获取参数和返回Response对象
		- apis.py: 定义几个错误异常类和Page类用于分页
		- config_default.py:默认的配置文件信息
		- config_override.py:自定义的配置文件信息
		- config.py:默认和自定义配置文件合并
		- markdown2.py:支持markdown显示的插件
		- test_orm.py: 用于测试orm框架的正确性


## orm.py实现思路

1. 实现ModelMetaclass，主要完成类属性域和特殊变量直接的映射关系，方便Model类中使用。同时可以定义一些默认的SQL处理语句

2. 实现Model类,包含基本的get,set方法用于获取和设置变量域的值。同时实现相应的SQL处理函数（这时候可以利用ModelMetaclass自动根据类实例封装好的特殊变量)

3. 实现基本的数据库类型类，在应用层用户只要使用这种数据库类型类即可，避免直接使用数据的类型增加问题复杂度

## web框架实现思路

web框架在此处主要用于对aiohttp库的方法做更高层次的封装，用于抽离一些可复用的操作简化过程。主要涉及的封装内容为：

 - 定义装饰器@get()和@post()用与自动获取URL路径中的基本信息
 - 定义RequestHandler类，该类的实例对象获取完整的URL参数信息并且调用对应的URL处理函数（类中的方法）
 - 定义add_router方法用于注册对应的方法，即找到合适的fn给app.router.add_route()方法。该方法是aiohttp提供的接口，用于指定URL处理函数

 综上，处理一个请求的过程即为：

 1. app.py中注册所有处理函数、初始化jinja2、添加静态文件路径
 2. 创建服务器监听线程
 3. 收到一个request请求
 4. 经过几个拦截器(middlewares)的处理(app.py中的app = web.Application..这条语句指定)
 5. 调用RequestHandler实例中的__call__方法；再调用__call__方法中的post或者get方法
 5. 从已经注册过的URL处理函数中(handler.py)中获取对应的URL处理方法


