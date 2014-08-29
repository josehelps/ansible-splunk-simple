import json
import logging
import cherrypy
import urlparse
import urllib

import splunk
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import jsonresponse, util, cached

logger = logging.getLogger('splunk.appserver.mrsparkle.custom_controllers.splunk_datapreview')

# define base URL parts for continue link after input add
FAILSAFE_CONTINUE_LINK = ['manager','search','data','inputs','monitor','_new']

class DataPreviewController(controllers.BaseController):
    '''
    Represents the data preview feature
    '''

    #
    # attach common template args
    #

    def render_template(self, template_path, template_args = {}):
        template_args['appList'] = self.get_app_manifest()
        return super(DataPreviewController, self).render_template(template_path, template_args)
    

    def get_app_manifest(self):
        '''
        Returns a dict of all available apps to current user
        '''
        output = cached.getEntities('apps/local', search=['disabled=false','visible=true'], count=-1)
        return output        
    

    #
    # routed controllers
    #

    @route('/')
    @expose_page()
    def prompt(self, **kwargs):

        # determine input type
        if kwargs.get('endpoint_base') == 'data/inputs/monitor':
            input_type = 'file'
        elif kwargs.get('endpoint_base') == 'data/inputs/tcp/raw':
            input_type = 'tcp'
        elif kwargs.get('endpoint_base') == 'data/inputs/udp':
            input_type = 'udp'
        else:
            input_type = None

        ns = kwargs.get('ns', splunk.getDefault('namespace'))
        bc = kwargs.get('breadcrumbs', '')
        crumbs = self.prepare_breadcrumbs(bc, ns)
        
        # get the preview limit
        props = splunk.bundle.getConf('limits')
        limit_bytes = 0
        try:
            limit_bytes = int(props['indexpreview']['max_preview_bytes'] or 0)
        except Exception, e:
            logger.warn('could not read preview indexing limit value from conf; skipping')

        if 'preview_continue_link' in cherrypy.session:
            continue_link = cherrypy.session['preview_continue_link']
        else:
            continue_link = self.make_url(FAILSAFE_CONTINUE_LINK, _qs={'preflight':'preview'})

        template_args = {
            'ns': ns,
            'input_type': input_type,
            'preview_limit_bytes': limit_bytes,
            'endpoint_base': kwargs.get('endpoint_base'),
            'cancel_link': util.make_url_internal(kwargs.get('return_to', self.make_url('/manager'))),
            'manual_link': continue_link,
            'breadcrumbs': crumbs,
            'source': kwargs.get('source',''),
            'preview_base_link': self.make_url(
                ['custom','splunk_datapreview','steps','preview']
            )
        }
        return self.render_template('/splunk_datapreview:/templates/prompt.html', template_args)


    @route('/=preview')
    @expose_page(must_login=True, methods=['GET'])
    def preview_edit(self, **kwargs):
        if 'preview_continue_link' in cherrypy.session:
            continue_link = cherrypy.session['preview_continue_link']
        else:
            continue_link = self.make_url(FAILSAFE_CONTINUE_LINK, _qs={'preflight':'preview'})

        ns = kwargs.get('ns', splunk.getDefault('namespace'))
        template_args = {
            'ns': kwargs.get('ns', splunk.getDefault('namespace')),
            'source': kwargs.get('source'),
            'continue_to': continue_link,
            'return_to': util.make_url_internal(kwargs.get('return_to')),
            'reset_to': kwargs.get('reset_to'),
            'breadcrumbs': self.prepare_breadcrumbs(kwargs.get('breadcrumbs',''), ns)
        }
        return self.render_template('/splunk_datapreview:/templates/edit.html', template_args)       

    def prepare_breadcrumbs(self, bc, ns):
        if len(bc) > 0:
            crumbs = util.parse_breadcrumbs_string(bc)
        else:
            crumbs = [[_('Manager'), self.make_url(['manager'], translate=False)],
                      [_('Data inputs'), self.make_url(['manager', ns, 'datainputstats'], translate=False)]]
        
        crumbs.extend([[_('Files & directories'), self.make_url(['manager', ns, 'data/inputs/monitor'], translate=False)],
                       [_('Data preview'), None]])
        
        return crumbs