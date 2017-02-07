#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
JSON API definition.
'''

import json, logging, inspect, functools

class Page(object):
    '''
    Page object for display pages.
    '''

    def __init__(self, item_count, page_index=1, page_size=10):
        '''init Pagination by item_count, page_index, page_size
        item_count - 博客总数
        page_index - 页码
        page_size - 一个页面最多显示博客的数目'''
        self.item_count = item_count # 从数据库中查询博客的总数获得
        self.page_size = page_size # 可自定义,或使用默认值
        # 页面数目,由博客总数与每页的博客数共同决定
        # item_count 不能被page_size整除时,最后一页的博客数目不满page_size,但仍需独立设立一页
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
        # 如果没有条目或者要显示的页超出了能显示的页的范围
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            # 否则说明要显示
            # 设置显示页就是传入的要求显示的页
            self.page_index = page_index
            # 这页的初始条目的offset
            self.offset = self.page_size * (page_index - 1)
            # 这页能显示的数量
            self.limit = self.page_size
        # 这页后面是否还有下一页
        self.has_next = self.page_index < self.page_count
        # 这页之前是否还有上一页
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__

class APIError(Exception):
    '''
    the base APIError which contains error(required), data(optional) and message(optional).
    '''
    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message

class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The data specifies the error field of input form.
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
