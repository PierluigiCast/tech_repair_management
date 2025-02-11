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

# Modello principale per la gestione delle riparazioni
class RepairOrder(models.Model):
    _name = 'tech.repair.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Attiva il tracking
    _description = 'Gestione Riparazioni'
    _order = 'create_date desc'  # Ordina per data di creazione (dal più recente)
    _logger = logging.getLogger(__name__)
    
    # Numero univoco della riparazione, generato automaticamente
    name = fields.Char(string='Numero Riparazione', required=True, copy=False, default=lambda self: self._generate_sequence())

    # Token
    token_url = fields.Char(string='Token URL', copy=False, readonly=True)


    # Cliente associato alla riparazione
    customer_id = fields.Many2one('res.partner', string='Cliente', required=True, context={'from_tech_repair_order': True})
    customer_mobile = fields.Char(string="Cell", related="customer_id.mobile", store=True)
    
    # categoria -> marca -> modello
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

    # stato complessivo del dispositivo all'accettazione
    aesthetic_state = fields.Char(string='Difetti Visivi', required=False , help="Se ci sono dei danni/graffi evidenti, scrivili qui")

    # seriale / IMEI e con traking registro i cambiamenti
    serial_number = fields.Char(string='Seriale / IMEI', required=False )

    # codice sime e password del dispositivo
    sim_pin = fields.Char(string="PIN SIM")
    device_password = fields.Char(string="Codice/Password Dispositivo")

    # eventuali extra user e password
    credential_ids = fields.One2many(
        'tech.repair.credential', 
        'tech_repair_order_id', 
        string="Credenziali"
    )

    # accessori lasciati dal cliente
    accessory_ids = fields.One2many(
        'tech.repair.accessory',
        'tech_repair_order_id', 
        string="Accessori",
    )

    # software da installare
    software_ids = fields.Many2many(
        'tech.repair.software',  
        'repair_software_rel',   # Nome della tabella di relazione
        'repair_id',             # Campo che collega a tech.repair.order
        'software_id',           # Campo che collega a tech.repair.software
        string='Software Installati'
    )



    # Stato Fittizio per la Visualizzazione Online
    customer_state_id = fields.Many2one(
        'tech.repair.state.public', 
        string="Stato Visibile al Cliente", 
    )

    # Laboratorio esterno a cui può essere inviata la riparazione
    external_lab_ids = fields.One2many(
        'tech.repair.external.lab',  # Collegamento al modello dei laboratori esterni
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



    # Tecnico assegnato alla riparazione (solo dipendenti) (automatizzato con default l'utente che carica la riparazione)
    assigned_to = fields.Many2one('res.users', string='Assegnato a', domain=[('employee', '=', True)], default=lambda self: self.env.user)

    # Tecnico che apre la riparazione (solo dipendenti) (automatizzato con default l'utente che carica la riparazione) (sola lettura)
    opened_by = fields.Many2one('res.users', string='Aperta da', domain=[('employee', '=', True)], default=lambda self: self.env.user, readonly=True)


    # Trova lo stato con sequence = 1 e lo imposta come predefinito
    def _default_state(self):
        state = self.env['tech.repair.state'].search([], order="sequence asc", limit=1)
        return state.id if state else None  # Se non trova stati, restituisce None senza errori

    # Stato della riparazione, gestito dinamicamente
    # Imposta lo stato automaticamente alla creazione

    state_id = fields.Many2one(
        'tech.repair.state',
         string='Stato', 
         required=True, 
         default=_default_state
        )

    # Descrizione del problema segnalato dal cliente
    problem_description = fields.Text(
        string='Descrizione Problema',
        help="Problema dichiarato dal cliente"
        )

    # Operazioni svolte dal tecnico
    # operations = fields.Text(string='Operazioni Svolte')
    operations = fields.Html(
        string="Operazioni Svolte",
        translate=True,
        sanitize=False,  # Permette HTML senza restrizioni (può essere utile se vuoi pulsanti o formattazione speciale)
        sanitize_attributes=False,
        help="Inserisci le operazioni e usa '/' per i comandi."
        )

    # Costo della riparazione
    tech_repair_cost = fields.Float(string='Costo Riparazione €', default=0.0)
    # Acconto versato dal cliente
    advance_payment = fields.Float(
        string='Acconto €', 
        default=0.0,
        help="Acconto"
        )
    # Sconto
    discount_amount = fields.Float(
        string="Sconto €",
        help="Importo dello sconto da applicare al totale."
    )

    # Calcolo automatico del totale previsto
    expected_total = fields.Float(string='Totale Previsto €', compute='_compute_expected_total')
    # Componenti usati per la riparazione, presi dal magazzino
    components_ids = fields.Many2many('product.product', string='Componenti Usati')

    # Dispositivo muletto assegnato temporaneamente al cliente
    loaner_device_id = fields.Many2one(
    'tech.repair.loaner_device', 
    string='Dispositivo Muletto',
    domain="[('status', '=', 'available')]",  # Mostra solo quelli disponibili
    
    )


    # Data di apertura (automaticamente impostata alla creazione)
    open_date = fields.Datetime(string='Data Apertura', default=lambda self: fields.Datetime.now(), readonly=True)


    # Data di chiusura come campo calcolato
    close_date = fields.Datetime(
        string='Data Chiusura',
        compute='_compute_close_date',
        store=True
    )

    last_modified_date = fields.Datetime(
    string="Ultima Modifica",
    readonly=True
    )

    renewal_date = fields.Date(string="Data di Rinnovo", compute="_compute_renewal_date", store=True, tracking=True)  # Scadenza della commessa


    chat_message_ids = fields.One2many(
        'tech.repair.chat.message',
        'tech_repair_order_id',
        string="Messaggi Chat"
    )

    new_message = fields.Text(string="Nuovo Messaggio", store=False)
    new_message_is_customer = fields.Boolean(string="Visibile al Cliente", store=False, default=False)

    # Firma digitale del cliente per la conferma della riparazione
    signature = fields.Binary(string='Firma Cliente')
    signature_locked = fields.Boolean(string="Firma Bloccata", default=True)

    signature_url = fields.Char("Firma Cliente URL", compute="_compute_signature_url", store=True)

    # Trova l'informativa predefinita
    def _default_term(self):
        term = self.env['tech.repair.term'].search([('predefinita', '=', True)], limit=1)
        return term.id if term else None  # Se non trova l'informativa, restituisce None senza errori

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

    
    
    # ------ CHATTER ------------

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



    # -------------------------- DEF

    @api.model_create_multi # Permette la creazione in batch
    def create(self, vals_list):

        # Trova l'informativa predefinita
        default_term = self.env['tech.repair.term'].search([('predefinita', '=', True)], limit=1)


        for vals in vals_list:

            # Se il campo 'name' non è presente nei valori, generiamo un numero di riparazione automatico
            if 'name' not in vals or not vals['name']:
                vals['name'] = self.env['ir.sequence'].next_by_code('tech.repair.order') or 'New'

            # Genera il token univoco per la riparazione
            if 'token_url' not in vals:
                vals['token_url'] = str(uuid.uuid4())  # Genera un token casuale

            # Imposta l'utente che crea la riparazione come assegnatario di default
            if 'assigned_to' not in vals:
                vals['assigned_to'] = self.env.uid
            
            # Imposta l'utente che crea la riparazione di default
            if 'opened_by' not in vals:
                vals['opened_by'] = self.env.uid

            # Imposta la data di apertura alla data e ora attuale
            vals['open_date'] = fields.Datetime.now()

            # Imposta automaticamente l'informativa predefinita
            if 'term_id' not in vals or not vals['term_id']:
                vals['term_id'] = default_term.id if default_term else None
            
            self._logger.info("Valori finali per la creazione: %s", vals)

        return super().create(vals_list)
        

    def write(self, vals):
        # Registra la data dell'ultima modifica e logga le modifiche nel Chatter
        if 'last_modified_date' not in vals:  # Evita un loop infinito aggiornando solo se non è già presente
            vals['last_modified_date'] = fields.Datetime.now()

        # Lista dei campi da ammettere per escludere il tracciamento doppio
        excluded_fields = ['signature']  # Variabile per i campi da escludere

        # Ottiene le etichette leggibili dei campi
        field_labels = self.fields_get()

        for record in self:
            old_values = {
                field: record[field] 
                for field in vals.keys() 
                if field in record and field not in excluded_fields  # Escludiamo alcuni campi
            }
            old_loaner = record.loaner_device_id  # Salvo il muletto precedente
            old_credentials = record.credential_ids  # Salvo le credenziali precedenti
            old_accessories = {acc.id: acc.name for acc in record.accessory_ids} # Salvo gli accessori prima della modifica
            

        res = super(RepairOrder, self).write(vals)  # Salvo prima le modifiche senza causare ricorsione

        for record in self:
            changed_fields = []

            # Controllo modifiche nei campi standard
            for field, old_value in old_values.items():
                new_value = record[field]

                # Evito il problema del False ➝ xxxx eliminando One2many / Many2one / Many2many
                if isinstance(record._fields[field], (fields.One2many, fields.Many2one, fields.Many2many)):
                    continue

                # Se il campo è Many2one, usa display_name
                if isinstance(old_value, models.Model) and isinstance(new_value, models.Model):
                    old_value = old_value.display_name
                    new_value = new_value.display_name

                # Se il campo è di tipo Selection, mostra la label invece del value
                if isinstance(record._fields[field], fields.Selection):
                    selection_dict = dict(record._fields[field].selection)  # Ottengo {value: label}
                    old_value = selection_dict.get(old_value, old_value)
                    new_value = selection_dict.get(new_value, new_value)

                if old_value != new_value:
                    field_name = field_labels[field]['string'] if field in field_labels else field
                    changed_fields.append(f"<strong>{field_name}</strong>: {old_value} ➝ <strong>{new_value}</strong>")
            
            # Blocco la firma dopo la modifica
            if 'signature' in vals:
                record.signature_locked = True
                #self.write({'signature_locked': True})  

            # Tracciamento modifiche accessori
            if 'accessory_ids' in vals:
                new_accessories = {acc.id: acc.name for acc in record.accessory_ids}

                # Troviamo accessori aggiunti
                added_accessories = [name for acc_id, name in new_accessories.items() if acc_id not in old_accessories]
                if added_accessories:
                    changed_fields.append(f"Aggiunti accessori: <strong>{', '.join(added_accessories)}</strong>")

                # Troviamo accessori rimossi
                removed_accessories = [name for acc_id, name in old_accessories.items() if acc_id not in new_accessories]
                if removed_accessories:
                    changed_fields.append(f"Rimossi accessori: <strong>{', '.join(removed_accessories)}</strong>")

                # Troviamo accessori modificati
                for acc_id, old_name in old_accessories.items():
                    if acc_id in new_accessories and old_name != new_accessories[acc_id]:
                        changed_fields.append(f"Modificato accessorio: <strong>{old_name} ➝ {new_accessories[acc_id]}</strong>")
                    # Se voglio rilevare le modifiche “interne” ai record accessori, devo confrontare i singoli campi
                    # Ad es. se i record già esistenti cambiano nome. In quell caso, devo implementarlo su accessor_id.

            # Tracciamento dello stato del muletto e aggiornamento del campo "Assegnato alla riparazione"
            if 'loaner_device_id' in vals:
                new_loaner = self.env['tech.repair.loaner_device'].browse(vals['loaner_device_id']) if vals['loaner_device_id'] else False

                # Se un nuovo muletto è stato assegnato
                if new_loaner:
                    new_loaner.status = 'assigned'
                    new_loaner.tech_repair_order_id = record.id  # Aggiorna il riferimento alla riparazione
                    changed_fields.append(f"Muletto assegnato: <strong>{new_loaner.name} ({new_loaner.serial_number})</strong>")

                # Se il muletto precedente è stato rimosso
                if old_loaner and old_loaner != new_loaner:
                    old_loaner.status = 'available'
                    old_loaner.tech_repair_order_id = False  # Rimuove il riferimento alla riparazione
                    changed_fields.append(f"Muletto reso disponibile: <strong>{old_loaner.name} ({old_loaner.serial_number})</strong>")

            # Tracciamento delle credenziali
            if 'credential_ids' in vals:
                new_credentials = record.credential_ids

                # Troviamo quali credenziali sono state aggiunte e quali rimosse
                # Se la versione di Odoo 18 dà problemi con l’operatore "-", bisogna usare la logica con .filtered()
                # es.:
                # added_credentials = new_credentials.filtered(lambda cred: cred.id not in old_credentials.ids)
                # removed_credentials = old_credentials.filtered(lambda cred: cred.id not in new_credentials.ids)
                added_credentials = new_credentials - old_credentials
                removed_credentials = old_credentials - new_credentials

                if added_credentials:
                    for cred in added_credentials:
                        service = cred.service_type if cred.service_type != 'other' else f"Altro ({cred.service_other})"
                        changed_fields.append(f"Aggiunta credenziale: <strong>{cred.username} / {cred.password}</strong> per <strong>{service}</strong>")

                if removed_credentials:
                    for cred in removed_credentials:
                        # Controlliamo se il record esiste ancora prima di accedere ai suoi campi
                        if cred.exists():
                            service = cred.service_type if cred.service_type != 'other' else f"Altro ({cred.service_other})"
                            changed_fields.append(f"Rimossa credenziale: <strong>{cred.username}</strong> per <strong>{service}</strong>")


                # Controllo modifiche nelle credenziali esistenti
                for cred in new_credentials:
                    old_cred = old_credentials.filtered(lambda c: c.id == cred.id)
                    if old_cred and len(old_cred) == 1:  # ✅ Evitiamo il problema del singleton
                        if old_cred.username != cred.username:
                            changed_fields.append(f"Modificato Username: <strong>{old_cred.username} ➝ {cred.username}</strong>")
                        if old_cred.password != cred.password:
                            changed_fields.append(f"Modificata Password per {cred.username}")
                        if old_cred.service_type != cred.service_type:
                            changed_fields.append(f"Modificato Servizio: <strong>{old_cred.service_type} ➝ {cred.service_type}</strong>")
                        if old_cred.service_other != cred.service_other and cred.service_type == 'other':
                            changed_fields.append(f"Modificato Servizio Altro: <strong>{old_cred.service_other} ➝ {cred.service_other}</strong>")


            # Se ci sono modifiche, registro il messaggio nel Chatter
            if changed_fields:
                message = "<strong>Modifiche effettuate:</strong><br/>" + "<br/>".join(changed_fields)
                record.message_post(
                    body=message,
                    message_type="notification",
                    subtype_id=self.env.ref("mail.mt_note").id,  # Attiva il Chatter
                    body_is_html=True  # Permette la formattazione HTML
                )

        return res

    # Impedisce la cancellazione delle commesse, consentendo solo l'archiviazione.
    def unlink(self):
        raise UserError("Le commesse di riparazione non possono essere eliminate. Puoi solo archiviarle.")

    def action_archive(self):
    # Archivia la commessa invece di eliminarla.
        self.write({'active': False})

    # Metodo per creare un numero di commessa automatico
    @api.model
    def _generate_sequence(self):
        # Genera automaticamente un numero di riparazione univoco
        return self.env['ir.sequence'].next_by_code('tech.repair.order') or 'Nuova Riparazione'


    # Quando un muletto viene assegnato, cambia il suo stato a 'Assegnato'
    @api.onchange('loaner_device_id')
    def _onchange_loaner_device(self):
        if self.loaner_device_id:
            self.loaner_device_id.status = 'assigned'

    @api.onchange('category_id')
    def _onchange_category_id(self):
        # Svuoto il campo 'model_id' e brand_id quando cambia il 'category_id'
        if self.category_id:
            self.model_id = False
            self.brand_id = False

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        # Svuoto il campo 'model_id' quando cambia il 'brand_id'
        if self.brand_id:
            self.model_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        # Se la riparazione viene mandata a un laboratorio esterno, il campo external_lab_id diventa obbligatorio.
        for record in self:
            if record.state_id.is_external_lab:
                if not record.external_lab_ids:
                    return {
                        'warning': {
                            'title': 'Attenzione',
                            'message': 'Questo stato richiede un laboratorio esterno!',
                        }
                    }
            # Aggiorno automaticamente lo stato visibile al cliente
            if record.state_id and record.state_id.public_state_id:
                record.customer_state_id = record.state_id.public_state_id
            else:
                record.customer_state_id = False  # Resetta se non c'è un mapping



    @api.depends('state_id')
    def _compute_close_date(self):
        for record in self:
            if record.state_id and record.state_id.is_closed:
                if not record.close_date:
                    record.close_date = fields.Datetime.now()


                    if record.id:  # Assicuro che il record sia già salvato
                        record.message_post(body=f"Stato cambiato a '{record.state_id.name}' e chiuso il {record.close_date.strftime('%Y-%m-%d %H:%M:%S')}.", message_type="notification")
            else:
                if record.close_date:  # Se lo stato non è più chiuso, rimuove la data
                    record.close_date = False
                    if record.id:  # Assicuro che il record sia già salvato
                        record.message_post(body=f"⚠ Stato riaperto. Data di chiusura rimossa.", message_type="notification")
    

    # Genera i QRCode
    @api.depends('name')
    def _generate_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.qr_code = self._generate_qr_code_for_url(f"{base_url}/repairstatus/{record.token_url}")
            

    @api.depends('name')
    def _generate_qr_code_int(self):
        # Genera un QR Code con il link diretto alla riparazione
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.qr_code_int = self._generate_qr_code_for_url(f"{base_url}/web#id={record.id}&model=tech.repair.order&view_type=form")
    
    # Genera un QR Code per un URL dato
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
    
    # Genera un URL per i QR Code e la firma sul report che non accetta l'immagine base64
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


    # Metodo per calcolare il totale previsto sottraendo l'acconto
    @api.depends('tech_repair_cost', 'advance_payment', 'components_ids', 'external_lab_ids.customer_cost', 'discount_amount')
    def _compute_expected_total(self):
        for record in self:
            component_cost = sum(record.components_ids.mapped('lst_price'))  # Somma i prezzi di listino dei componenti
            lab_cost = sum(record.external_lab_ids.mapped('customer_cost'))  # Somma costi di tutti i laboratori
            software_cost = sum(record.software_ids.mapped('price'))  # Somma i costi dei software
            record.expected_total = (
                record.tech_repair_cost + 
                software_cost + 
                lab_cost + 
                component_cost
                ) - record.advance_payment - record.discount_amount


    # Calcola la scadenza della commessa in base al software con durata maggiore
    @api.depends('software_ids', 'close_date')
    def _compute_renewal_date(self):
        for record in self:
            if record.software_ids and record.close_date:
                # Trova la durata massima tra i software installati
                max_duration = max(int(software.duration) for software in record.software_ids)
                record.renewal_date = record.close_date + timedelta(days=max_duration * 30)
            else:
                record.renewal_date = False

    # Controlla le commesse in scadenza e invia un'email di promemoria 1 mese prima
    @api.model
    def check_repair_renewals(self):
        today = fields.Date.today()
        renewal_alert_date = today + timedelta(days=30)  # 1 mese prima della scadenza

        # Trova le commesse con scadenza tra 30 giorni
        orders_to_renew = self.search([
            ('renewal_date', '=', renewal_alert_date),
            ('customer_id', '!=', False)
        ])

        mail_template = self.env.ref('tech_repair_management.email_template_repair_renewal')

        for order in orders_to_renew:
            # Invia una mail al cliente
            if mail_template:
                mail_template.send_mail(order.customer_id.id, force_send=True)

            # Crea un'opportunità CRM per il rinnovo della commessa
            self.crm_lead_creation(order)

    # Forza l'invio dell'email di rinnovo al cliente
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
                    'email_from': f"{record.company_id.name} <{record.company_id.email or ''}>", # se vuoto, imposta quello configurato
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

        # Cerca se esiste già l'etichetta "Rinnovi"
        renewal_tag = crm_tag.search([('name', '=', 'Rinnovi')], limit=1)

        # Se l'etichetta non esiste, la crea
        if not renewal_tag:
            renewal_tag = crm_tag.create({'name': 'Rinnovi'})
        
        self.env['crm.lead'].create({
                    'name': f"Rinnovo Software - {record.customer_id.name}",
                    'partner_id': record.customer_id.id,
                    'type': 'opportunity',
                    'tag_ids': [(4, renewal_tag.id)],  # Assegna l'etichetta "Rinnovi"
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


    # Gestione del tasto invia messaggio al cliente online
    def action_send_message(self):
        for record in self:
            if record.new_message:
                self.env['tech.repair.chat.message'].create({
                    'tech_repair_order_id': record.id,
                    'sender': 'technician',
                    'message': record.new_message,
                })

                # Aggiungo il messaggio del tecnico nel Chatter
                record.sudo().message_post(
                    body=f"<strong>Risposta Tecnico:</strong> {record.new_message}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                    body_is_html=True  # Permette la formattazione HTML
                )
                record.new_message = ""

    
    # Salva la riparazione e mostra una notifica di conferma
    def action_save_repair(self):
        for record in self:
            record.message_post(body="La riparazione è stata salvata con successo.", message_type="notification")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Successo!',
                'message': 'Riparazione salvata con successo!',
                'sticky': False,  # Se True, la notifica rimane visibile finché l'utente non la chiude
                'type': 'success',  # Può essere 'success', 'warning', 'danger'
            }
        }

    # Azione per stampare il report della riparazione 
    def action_print_repair_report(self):
        return self.env.ref('tech_repair_management.action_report_repair_order').report_action(self)

                

    # Metodo per creare un ordine di vendita manualmente dalle riparazioni
    def action_create_sale_order(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'order_line': [(0, 0, {'product_id': comp.id, 'price_unit': comp.lst_price}) for comp in self.components_ids]
        })
        return sale_order

    # sblocca la firma
    def action_unlock_signature(self):
        self.write({'signature_locked': False})
    
    # Ricerca per QRCode
    @api.model
    def search_by_qr(self, qr_code_value):
        # Cerca una riparazione in base al numero scansionato dal QR Code
        return self.search([('name', '=', qr_code_value)], limit=1)
