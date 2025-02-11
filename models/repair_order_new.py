import logging
import base64
import qrcode
import os
import uuid
from io import BytesIO
from odoo import models, fields, api
from odoo.tools import config
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class RepairOrder(models.Model):
    _name = 'tech.repair.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Gestione Riparazioni'
    _order = 'create_date desc'
    _logger = logging.getLogger(__name__)

    name = fields.Char(
        string='Numero Riparazione', 
        required=True, 
        copy=False, 
        default=lambda self: self._generate_sequence()
    )
    token_url = fields.Char(string='Token URL', copy=False, readonly=True)
    customer_id = fields.Many2one('res.partner', string='Cliente', required=True, context={'from_tech_repair_order': True})
    customer_mobile = fields.Char(string="Cell", related="customer_id.mobile", store=True)
    
    category_id = fields.Many2one('tech.repair.device.category', string='Categoria', required=True)
    brand_id = fields.Many2one('tech.repair.device.brand', string='Marca', required=True)
    model_id = fields.Many2one('tech.repair.device.model', string='Modello', required=True)

    device_color = fields.Many2one(
        'tech.repair.device.color',
        string="Colore",
        help="Seleziona il colore del dispositivo",
    )
    aesthetic_condition = fields.Selection([
        ('new', 'Nuovo'),
        ('good', 'Buono'),
        ('used', 'Usato'),
        ('damaged', 'Danneggiato')
    ], string='Stato Estetico', default='good')
    aesthetic_state = fields.Char(string='Difetti Visivi', help="Se ci sono danni/graffi evidenti, scrivili qui")
    serial_number = fields.Char(string='Seriale / IMEI')
    sim_pin = fields.Char(string="PIN SIM")
    device_password = fields.Char(string="Codice/Password Dispositivo")

    credential_ids = fields.One2many(
        'tech.repair.credential',
        'tech_repair_order_id',
        string="Credenziali"
    )

    accessory_ids = fields.One2many(
        'tech.repair.accessory',
        'tech_repair_order_id',
        string="Accessori",
    )

    software_ids = fields.Many2many(
        'tech.repair.software',
        'repair_software_rel',
        'repair_id',
        'software_id',
        string='Software Installati'
    )

    customer_state_id = fields.Many2one(
        'tech.repair.state.public',
        string="Stato Visibile al Cliente",
    )

    external_lab_ids = fields.One2many(
        'tech.repair.external.lab',
        'tech_repair_order_id',
        string='Laboratori Esterni'
    )

    qr_code = fields.Binary(
        string="QR Code Cliente",
        compute="_generate_qr_code",
        store=True
    )
    qr_code_url = fields.Char("QR Code URL", compute="_compute_qr_code_url", store=True)

    qr_code_int = fields.Binary(
        string="QR Code Interno",
        compute="_generate_qr_code_int",
        store=True
    )
    qr_code_int_url = fields.Char("QR Code URL", compute="_compute_qr_code_int_url", store=True)

    assigned_to = fields.Many2one('res.users', string='Assegnato a', domain=[('employee', '=', True)], default=lambda self: self.env.user)
    opened_by = fields.Many2one('res.users', string='Aperta da', domain=[('employee', '=', True)], default=lambda self: self.env.user, readonly=True)

    def _default_state(self):
        state = self.env['tech.repair.state'].search([], order="sequence asc", limit=1)
        return state.id if state else None

    state_id = fields.Many2one(
        'tech.repair.state',
        string='Stato',
        required=True,
        default=_default_state
    )

    problem_description = fields.Text(
        string='Descrizione Problema',
        help="Problema dichiarato dal cliente"
    )
    operations = fields.Html(
        string="Operazioni Svolte",
        translate=True,
        sanitize=False,
        sanitize_attributes=False,
        help="Inserisci le operazioni e usa '/' per i comandi."
    )
    tech_repair_cost = fields.Float(string='Costo Riparazione €', default=0.0)
    advance_payment = fields.Float(string='Acconto €', default=0.0, help="Acconto")
    discount_amount = fields.Float(string="Sconto €", help="Importo dello sconto da applicare al totale.")

    # Calcolo del totale con mapped() per evitare problemi di singleton
    @api.depends('tech_repair_cost', 'advance_payment', 'components_ids', 'external_lab_ids.customer_cost', 'discount_amount', 'software_ids')
    def _compute_expected_total(self):
        for record in self:
            component_cost = sum(record.components_ids.mapped('lst_price'))  # corretto uso di mapped
            lab_cost = sum(record.external_lab_ids.mapped('customer_cost'))
            software_cost = sum(record.software_ids.mapped('price'))
            record.expected_total = (
                record.tech_repair_cost +
                software_cost +
                lab_cost +
                component_cost
            ) - record.advance_payment - record.discount_amount

    expected_total = fields.Float(string='Totale Previsto €', compute='_compute_expected_total')

    components_ids = fields.Many2many('product.product', string='Componenti Usati')
    loaner_device_id = fields.Many2one(
        'tech.repair.loaner_device',
        string='Dispositivo Muletto',
        domain="[('status', '=', 'available')]",
    )

    open_date = fields.Datetime(string='Data Apertura', default=lambda self: fields.Datetime.now(), readonly=True)
    close_date = fields.Datetime(string='Data Chiusura', compute='_compute_close_date', store=True)
    last_modified_date = fields.Datetime(string="Ultima Modifica", readonly=True)
    
    @api.depends('state_id')
    def _compute_close_date(self):
        for record in self:
            if record.state_id and record.state_id.is_closed:
                if not record.close_date:
                    record.close_date = fields.Datetime.now()
                    if record.id:
                        record.message_post(
                            body=(
                                f"Stato cambiato a '{record.state_id.name}' "
                                f"e chiuso il {record.close_date.strftime('%Y-%m-%d %H:%M:%S')}."
                            ),
                            message_type="notification"
                        )
            else:
                if record.close_date:
                    record.close_date = False
                    if record.id:
                        record.message_post(
                            body="⚠ Stato riaperto. Data di chiusura rimossa.",
                            message_type="notification"
                        )

    renewal_date = fields.Date(string="Data di Rinnovo", compute="_compute_renewal_date", store=True, tracking=True)

    @api.depends('software_ids', 'close_date')
    def _compute_renewal_date(self):
        """Calcola la scadenza in base al software con la durata maggiore."""
        for record in self:
            if record.software_ids and record.close_date:
                # evita max() su un recordset vuoto
                max_duration = max(int(software.duration) for software in record.software_ids)
                record.renewal_date = record.close_date + timedelta(days=max_duration * 30)
            else:
                record.renewal_date = False

    chat_message_ids = fields.One2many(
        'tech.repair.chat.message',
        'tech_repair_order_id',
        string="Messaggi Chat"
    )
    new_message = fields.Text(string="Nuovo Messaggio", store=False)
    new_message_is_customer = fields.Boolean(string="Visibile al Cliente", store=False, default=False)

    signature = fields.Binary(string='Firma Cliente')
    signature_locked = fields.Boolean(string="Firma Bloccata", default=True)
    signature_url = fields.Char("Firma Cliente URL", compute="_compute_signature_url", store=True)

    def _default_term(self):
        term = self.env['tech.repair.term'].search([('predefinita', '=', True)], limit=1)
        return term.id if term else None

    term_id = fields.Many2one(
        'tech.repair.term',
        string="Informativa",
        help="Seleziona l'informativa da allegare alla riparazione.",
        default=_default_term
    )

    company_id = fields.Many2one(
        'res.company',
        string="Azienda",
        required=True,
        default=lambda self: self.env.company
    )

    message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name)],
        string='Messaggi del Chatter'
    )
    message_follower_ids = fields.One2many(
        'mail.followers', 'res_id',
        domain=lambda self: [('res_model', '=', self._name)],
        string='Followers'
    )
    active = fields.Boolean(default=True, string="Attivo", help="Se deselezionato, la commessa è archiviata.")

    @api.model_create_multi
    def create(self, vals_list):
        default_term = self.env['tech.repair.term'].search([('predefinita', '=', True)], limit=1)
        for vals in vals_list:
            if 'name' not in vals or not vals['name']:
                vals['name'] = self.env['ir.sequence'].next_by_code('tech.repair.order') or 'New'
            if 'token_url' not in vals:
                vals['token_url'] = str(uuid.uuid4())
            if 'assigned_to' not in vals:
                vals['assigned_to'] = self.env.uid
            if 'opened_by' not in vals:
                vals['opened_by'] = self.env.uid
            vals['open_date'] = fields.Datetime.now()
            if 'term_id' not in vals or not vals['term_id']:
                vals['term_id'] = default_term.id if default_term else None

            self._logger.info("Valori finali per la creazione: %s", vals)
        return super().create(vals_list)

    def write(self, vals):
        # Aggiorno la data di ultima modifica
        if 'last_modified_date' not in vals:
            vals['last_modified_date'] = fields.Datetime.now()

        # Campi da escludere dal tracciamento di test
        excluded_fields = ['signature']

        # Aggiungiamo il Many2many se vogliamo saltare il tracciamento di quei campi
        # Esempio: if you want to skip them:
        # if 'components_ids' in vals: ...
        # Per ora manteniamo la logica attuale.

        field_labels = self.fields_get()

        for record in self:
            old_values = {
                field: record[field]
                for field in vals.keys()
                if field in record and field not in excluded_fields
            }
            old_loaner = record.loaner_device_id
            old_credentials = record.credential_ids
            old_accessories = {acc.id: acc.name for acc in record.accessory_ids}

        res = super(RepairOrder, self).write(vals)

        for record in self:
            changed_fields = []

            # Controllo modifiche nei campi "standard"
            for field, old_value in old_values.items():
                new_value = record[field]

                # Saltiamo i campi One2many, Many2one o Many2many nelle differenze string literal
                if isinstance(record._fields[field], (fields.One2many, fields.Many2one, fields.Many2many)):
                    continue

                if isinstance(old_value, models.Model) and isinstance(new_value, models.Model):
                    old_value = old_value.display_name
                    new_value = new_value.display_name

                # Per le Selection, mostriamo la label anziché il valore
                if isinstance(record._fields[field], fields.Selection):
                    selection_dict = dict(record._fields[field].selection)
                    old_value = selection_dict.get(old_value, old_value)
                    new_value = selection_dict.get(new_value, new_value)

                if old_value != new_value:
                    field_name = field_labels[field]['string'] if field in field_labels else field
                    changed_fields.append(
                        f"<strong>{field_name}</strong>: {old_value} ➝ <strong>{new_value}</strong>"
                    )

            # Blocco la firma se viene modificata
            if 'signature' in vals:
                record.signature_locked = True

            # Tracciamento modifiche sugli accessori
            if 'accessory_ids' in vals:
                new_accessories = {acc.id: acc.name for acc in record.accessory_ids}
                added_accessories = [
                    name for acc_id, name in new_accessories.items()
                    if acc_id not in old_accessories
                ]
                if added_accessories:
                    changed_fields.append(
                        f"Aggiunti accessori: <strong>{', '.join(added_accessories)}</strong>"
                    )

                removed_accessories = [
                    name for acc_id, name in old_accessories.items()
                    if acc_id not in new_accessories
                ]
                if removed_accessories:
                    changed_fields.append(
                        f"Rimossi accessori: <strong>{', '.join(removed_accessories)}</strong>"
                    )

                # Se vuoi anche rilevare modifiche “interne” ai record accessori, devi confrontare i singoli campi
                # Ad es. se i record già esistenti cambiano nome. In quell caso, va implementato su accessor_id.

            # Gestione stato del muletto
            if 'loaner_device_id' in vals:
                new_loaner_id = vals['loaner_device_id']
                new_loaner = self.env['tech.repair.loaner_device'].browse(new_loaner_id) if new_loaner_id else False

                # Muletto aggiunto
                if new_loaner:
                    new_loaner.status = 'assigned'
                    new_loaner.tech_repair_order_id = record.id
                    changed_fields.append(
                        f"Muletto assegnato: <strong>{new_loaner.name} ({new_loaner.serial_number})</strong>"
                    )

                # Muletto precedente rimosso
                if old_loaner and old_loaner != new_loaner:
                    old_loaner.status = 'available'
                    old_loaner.tech_repair_order_id = False
                    changed_fields.append(
                        f"Muletto reso disponibile: <strong>{old_loaner.name} ({old_loaner.serial_number})</strong>"
                    )

            # Tracciamento credenziali
            if 'credential_ids' in vals:
                new_credentials = record.credential_ids

                # Se la tua versione di Odoo dà problemi con l’operatore "-", usa la logica con .filtered()
                # es.:
                # added_credentials = new_credentials.filtered(lambda cred: cred.id not in old_credentials.ids)
                # removed_credentials = old_credentials.filtered(lambda cred: cred.id not in new_credentials.ids)

                added_credentials = new_credentials - old_credentials
                removed_credentials = old_credentials - new_credentials

                if added_credentials:
                    for cred in added_credentials:
                        service = (
                            cred.service_type
                            if cred.service_type != 'other'
                            else f"Altro ({cred.service_other})"
                        )
                        changed_fields.append(
                            f"Aggiunta credenziale: <strong>{cred.username} / {cred.password}</strong> per <strong>{service}</strong>"
                        )

                if removed_credentials:
                    for cred in removed_credentials:
                        # Attenzione a cred.exists() se la tua versione lo supporta regolarmente
                        if cred.exists():
                            service = (
                                cred.service_type
                                if cred.service_type != 'other'
                                else f"Altro ({cred.service_other})"
                            )
                            changed_fields.append(
                                f"Rimossa credenziale: <strong>{cred.username}</strong> per <strong>{service}</strong>"
                            )

                # Controllo eventuali modifiche su credenziali esistenti
                for cred in new_credentials:
                    old_cred = old_credentials.filtered(lambda c: c.id == cred.id)
                    if old_cred and len(old_cred) == 1:
                        if old_cred.username != cred.username:
                            changed_fields.append(
                                f"Modificato Username: <strong>{old_cred.username} ➝ {cred.username}</strong>"
                            )
                        if old_cred.password != cred.password:
                            changed_fields.append(
                                f"Modificata Password per {cred.username}"
                            )
                        if old_cred.service_type != cred.service_type:
                            changed_fields.append(
                                f"Modificato Servizio: <strong>{old_cred.service_type} ➝ {cred.service_type}</strong>"
                            )
                        if old_cred.service_other != cred.service_other and cred.service_type == 'other':
                            changed_fields.append(
                                f"Modificato Servizio Altro: <strong>{old_cred.service_other} ➝ {cred.service_other}</strong>"
                            )

            # Se abbiamo modifiche, le inseriamo nel chatter
            if changed_fields:
                message = "<strong>Modifiche effettuate:</strong><br/>" + "<br/>".join(changed_fields)
                record.message_post(
                    body=message,
                    message_type="notification",
                    subtype_id=self.env.ref("mail.mt_note").id,
                    body_is_html=True
                )

        return res

    def unlink(self):
        raise UserError("Le commesse di riparazione non possono essere eliminate. Puoi solo archiviarle.")

    def action_archive(self):
        self.write({'active': False})

    @api.model
    def _generate_sequence(self):
        return self.env['ir.sequence'].next_by_code('tech.repair.order') or 'Nuova Riparazione'

    @api.onchange('loaner_device_id')
    def _onchange_loaner_device(self):
        if self.loaner_device_id:
            self.loaner_device_id.status = 'assigned'

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.model_id = False
            self.brand_id = False

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            self.model_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        for record in self:
            if record.state_id.is_external_lab:
                if not record.external_lab_ids:
                    return {
                        'warning': {
                            'title': 'Attenzione',
                            'message': 'Questo stato richiede un laboratorio esterno!',
                        }
                    }
            if record.state_id and record.state_id.public_state_id:
                record.customer_state_id = record.state_id.public_state_id
            else:
                record.customer_state_id = False

    @api.depends('name')
    def _generate_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.qr_code = self._generate_qr_code_for_url(f"{base_url}/repairstatus/{record.token_url}")

    @api.depends('name')
    def _generate_qr_code_int(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.qr_code_int = self._generate_qr_code_for_url(
                f"{base_url}/web#id={record.id}&model=tech.repair.order&view_type=form"
            )

    def _generate_qr_code_for_url(self, url):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue())

    @api.depends('qr_code')
    def _compute_qr_code_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.qr_code:
                record.qr_code_url = f"{base_url}/web/image/{record._name}/{record.id}/qr_code"
            else:
                record.qr_code_url = False

    @api.depends('qr_code_int')
    def _compute_qr_code_int_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.qr_code_int:
                record.qr_code_int_url = f"{base_url}/web/image/{record._name}/{record.id}/qr_code_int"
            else:
                record.qr_code_int_url = False

    @api.depends('signature')
    def _compute_signature_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.signature:
                record.signature_url = f"{base_url}/web/image/{record._name}/{record.id}/signature"
            else:
                record.signature_url = False

    def check_repair_renewals(self):
        """Controlla scadenze e invia mail di rinnovo."""
        today = fields.Date.today()
        renewal_alert_date = today + timedelta(days=30)
        orders_to_renew = self.search([
            ('renewal_date', '=', renewal_alert_date),
            ('customer_id', '!=', False)
        ])
        mail_template = self.env.ref('tech_repair_management.email_template_repair_renewal')
        for order in orders_to_renew:
            if mail_template:
                mail_template.send_mail(order.customer_id.id, force_send=True)
            self.crm_lead_creation(order)

    def action_force_send_renewal_email(self):
        mail_template = self.env.ref('tech_repair_management.email_template_repair_renewal')
        for record in self:
            if not record.renewal_date:
                raise UserError("Nessuna data di rinnovo impostata.")
            if not record.customer_id.email:
                raise UserError(f"Il cliente {record.customer_id.name} non ha un'email impostata!")
            if mail_template:
                email_values = {
                    'email_to': record.customer_id.email,
                    'email_from': f"{record.company_id.name} <{record.company_id.email or ''}>",
                    'body_html': mail_template.body_html
                        .replace('${object.customer_id.name}', record.customer_id.name)
                        .replace('${object.renewal_date}', str(record.renewal_date)),
                }
                mail_template.send_mail(record.id, force_send=True, email_values=email_values)
                record.message_post(
                    body=f"⚡ Email di rinnovo inviata manualmente a {record.customer_id.email}.",
                    message_type="comment"
                )
                self.crm_lead_creation(record)

    def crm_lead_creation(self, record):
        crm_lead = self.env['crm.lead']
        crm_tag = self.env['crm.tag']
        renewal_tag = crm_tag.search([('name', '=', 'Rinnovi')], limit=1)
        if not renewal_tag:
            renewal_tag = crm_tag.create({'name': 'Rinnovi'})

        crm_lead.create({
            'name': f"Rinnovo Software - {record.customer_id.name}",
            'partner_id': record.customer_id.id,
            'type': 'opportunity',
            'tag_ids': [(4, renewal_tag.id)],
            'description': f"""
                <p>Rinnovo software della commessa 
                <strong><a href="{self.env['ir.config_parameter'].sudo().get_param('web.base.url')}/web#id={record.id}&model=tech.repair.order&view_type=form">{record.name}</a></strong>
                per <strong>{record.customer_id.name}</strong>.</p>
                <p><strong>Scadenza:</strong> {record.renewal_date.strftime('%d/%m/%Y') if record.renewal_date else 'Data non disponibile'}</p>
                <p><strong>Contatto:</strong> {record.customer_id.mobile or 'Non disponibile'}</p>
                <p><strong>Mail:</strong> {record.customer_id.email or 'Non disponibile'}</p>
                <p><strong>Software da rinnovare:</strong></p>
                <ul>
                    {"".join([f"<li>{software.name} - €{software.price:.2f}</li>" for software in record.software_ids])}
                </ul>
            """,
            'expected_revenue': sum(record.software_ids.mapped('price')),
            'probability': 50,
        })

    def action_send_message(self):
        """Invia il messaggio del tecnico nella chat interna e nel chatter."""
        for record in self:
            if record.new_message:
                self.env['tech.repair.chat.message'].create({
                    'tech_repair_order_id': record.id,
                    'sender': 'technician',
                    'message': record.new_message,
                })
                record.sudo().message_post(
                    body=f"<strong>Risposta Tecnico:</strong> {record.new_message}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                    body_is_html=True
                )
                record.new_message = ""

    def action_save_repair(self):
        for record in self:
            record.message_post(
                body="La riparazione è stata salvata con successo.", 
                message_type="notification"
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Successo!',
                'message': 'Riparazione salvata con successo!',
                'sticky': False,
                'type': 'success',
            }
        }

    def action_print_repair_report(self):
        return self.env.ref('tech_repair_management.action_report_repair_order').report_action(self)

    def action_create_sale_order(self):
        """Esempio: crea ordine di vendita dai componenti usati."""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'order_line': [
                (0, 0, {'product_id': comp.id, 'price_unit': comp.lst_price})
                for comp in self.components_ids
            ]
        })
        return sale_order

    def action_unlock_signature(self):
        """Sblocca la firma per permettere al cliente di rifirmare."""
        self.write({'signature_locked': False})

    @api.model
    def search_by_qr(self, qr_code_value):
        """Cerca una riparazione in base al contenuto scansionato dal QR Code."""
        return self.search([('name', '=', qr_code_value)], limit=1)
