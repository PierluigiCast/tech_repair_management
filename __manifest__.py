{
    'name': 'TECH 3.0 Srl Riparazioni',
    'version': '1.0',
    'summary': 'Commesse Riparazioni in Odoo 18',
    'description': 'Aggiunge funzionalità delle commesse di riparazione by TECH 3.0 Srl',
    'author': 'TECH 3.0 Srl',
    'category': 'Services',
    'depends': ['base', 'sale', 'product', 'web', 'website', 'website_payment', 'mail', 'contacts', 'crm'],
    'data': [
        'views/repair_order_views.xml',
        # 'views/repair_order_kanban.xml',
        # 'views/qrcodeweb/repair_management_views.xml',
        'views/qrcodeweb/repair_status_page.xml',
        'views/configurazione/repair_device_views.xml',
        'views/configurazione/repair_loaner_views.xml',
        'views/configurazione/repair_category_views.xml',
        'views/configurazione/repair_brand_views.xml',
        'views/configurazione/repair_model_views.xml',
        'views/configurazione/repair_state_views.xml',
        'views/configurazione/repair_state_public_views.xml',
        'views/configurazione/repair_device_color_views.xml',
        'views/configurazione/repair_term_views.xml',
        'views/configurazione/repair_software.xml',
        'views/report/repair_order_report.xml',
        
        'views/repair_management_main_menu.xml',
        
        'security/ir.model.access.csv',

        'data/repair_state_public.xml',
        'data/repair_state_data.xml',
        'data/repair_order_sequence.xml',
        'data/device_data.xml',
        'data/repair_term.xml',
        'data/cron_job.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tech_repair_management/static/src/css/custom_styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3'
}