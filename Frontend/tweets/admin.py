from django.contrib import admin
from tweets.models import Tweet, Source, Keyword
# Register your models here.

import os, yaml

class SourceInline(admin.TabularInline):
    model = Source
    fields = ['url']
    extra = 0

class KeywordInline(admin.TabularInline):
    model = Keyword
    extra = 0

class TweetAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['tweet_id', 'name', 'text']}),
        ('Date information', {'fields': ['date_added', 'date_published']})
        ]

    inlines = [SourceInline, KeywordInline]

    list_display = ('link_user', 'link_id', 'text', 'get_keywords', 'get_sources', 'date_published', 'date_added', 'link_options')

    search_fields = ['tweet_id', 'text', 'user', 'keyword__name', 'source__url']
    list_filter = ['name', 'keyword__name', 'source__domain']
    ordering = ['-date_added']
    actions_on_top = True


    def get_keywords(self, obj):
        keywords = ''
        for key in obj.keyword_set.all():
            keywords += key.name + ', '
        return keywords[:-2]

    get_keywords.short_description = 'Matched Keywords'
    get_keywords.admin_order_field = 'keyword__name'

    def get_sources(self, obj):
        sources = ''
        for src in obj.source_set.all():
            if 'http://www.' in src.url:
                link = 'http://' + src.url[11:]
            else:
                link = src.url
            sources += format('<a href="%s" target="_blank">%s</a>' % (link, link))
            sources += '<br>'
        return sources[:-4]

    get_sources.short_description = 'Matched Sources'
    get_sources.admin_order_field = 'source__url'
    get_sources.allow_tags = True

    def link_id(self, obj):
        return format('<a href="%s" target="_blank">%s</a>' % ("https://twitter.com/" + obj.name + "/status/" + str(obj.tweet_id),
                                               obj.tweet_id))

    link_id.allow_tags = True
    link_id.admin_order_field = 'tweet_id'
    link_id.short_description = "Tweet ID"

    def link_user(self, obj):
        return format('<a href="%s" target="_blank">%s</a>' % ("https://twitter.com/" + obj.name,
                                               obj.name))

    link_user.allow_tags = True
    link_user.admin_order_field = 'name'
    link_user.short_description = "User"


    def link_options(self, obj):
        return format(('<a href="/admin/tweets/tweet/%s">Details</a><br>' +\
                       '<a href="/tweets/warc/%s">Download</a>') % (str(obj.pk), 'https:__twitter.com_' + obj.name + '_status_' + str(obj.tweet_id)))


    link_options.allow_tags = True
    link_options.short_description = "Options"

admin.site.register(Tweet, TweetAdmin)
