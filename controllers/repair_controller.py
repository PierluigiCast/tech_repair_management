from odoo import http
from odoo.http import request
import logging


class RepairController(http.Controller):

    _logger = logging.getLogger(__name__)

    # stringa pubblica per visualizzare la commessa
    @http.route('/repairstatus/<string:token>', type='http', auth="public", website=True)
    def tech_repair_status(self, token, **kwargs):
        # Forzo Odoo a usare un db
        db_name = request.httprequest.args.get('db')
        if db_name:
            request.session.db = db_name
            
        tech_repair_order = request.env['tech.repair.order'].sudo().search([('token_url', '=', token)], limit=1)


        # if not tech_repair_order.exists(): vista da creare se non trova la riparazione
        #     return request.render('tech_repair_management.tech_repair_order', {})

        # Filtra solo i messaggi destinati al cliente
        chat_messages = request.env['tech.repair.chat.message'].sudo().search([
            ('tech_repair_order_id.token_url', '=', token)
        ], order='create_date asc')

        # Log per debug
        self._logger.info("Messaggi trovati per la riparazione %s: %s", token, chat_messages)


        return request.render('tech_repair_management.tech_repair_status_page', {
            'repair': tech_repair_order,
            'customer_state': tech_repair_order.customer_state_id.name if tech_repair_order.customer_state_id else "Stato non ancora disponibile",
            'open_date': tech_repair_order.open_date.strftime('%d/%m/%Y %H:%M') if tech_repair_order.open_date else "Data non disponibile",
            'chat_messages': chat_messages
        })

    # stringa pubblica per inviare i messaggi
    @http.route('/repairstatus/send_message', type='http', auth="public", methods=['POST'], website=True)
    def send_message(self, **post):
        token = post.get('token')
        customer_message = post.get('customer_message')  # Nome corretto del campo dal form

        if token and customer_message:
            tech_repair_order = request.env['tech.repair.order'].sudo().search([('token_url', '=', token)], limit=1)
            if tech_repair_order.exists():
                # Salvo il messaggio nella tabella `tech.repair.chat.message`
                request.env['tech.repair.chat.message'].sudo().create({
                    'tech_repair_order_id': tech_repair_order.id,
                    'sender': 'customer',  # Indico che è un messaggio del cliente
                    'message': customer_message
                })

                # Aggiungiamo il messaggio al Chatter
                tech_repair_order.message_post(
                    body=f"<strong>Messaggio dal Cliente:</strong> {customer_message}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                    body_is_html=True  # Permette la formattazione HTML
                )

                #self._logger.info("Messaggio ricevuto dal cliente per riparazione %s: %s", token, customer_message)

        return request.redirect(f'/repairstatus/{token}')



    # stringa pubblica per generare il pdf tramite token
    @http.route('/repairstatus/pdf/<string:token>', type='http', auth="public", website=True)
    def download_repair_pdf(self, token, **kwargs):
        
        repair_order = request.env['tech.repair.order'].sudo().search([('token_url', '=', token)], limit=1)

        if not repair_order.exists():
            #self._logger.error(f"Nessuna riparazione trovata per il token: {token}")
            return request.not_found()

        #self._logger.info(f"Riparazione trovata - ID: {repair_order.id}, Nome: {repair_order.name}")

        # Recupera il report di Odoo
        report_action = request.env.ref('tech_repair_management.action_report_repair_order', raise_if_not_found=False)
        if not report_action:
            #self._logger.error("Errore: Il report non esiste in Odoo")
            return request.make_response("Errore: Il report non esiste.", [('Content-Type', 'text/plain')])

        # Genera il PDF con un ID singolo (non una lista)
        try:
            # Genera il PDF usando il nome del report
            pdf_content, content_type = request.env['ir.actions.report']._render_qweb_pdf(
                'tech_repair_management.action_report_repair_order', [repair_order.id]
            )
            #self._logger.info(f"PDF generato con successo per ID: {repair_order.id}")

        except Exception as e:
            #self._logger.error(f"Errore nella generazione del PDF: {str(e)}")
            return request.make_response(f"Errore nella generazione del PDF: {str(e)}", [('Content-Type', 'text/plain')])

            # Ritorna il PDF come risposta
        pdf_filename = f"Riparazione_{repair_order.name}.pdf"
        return request.make_response(pdf_content, [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'attachment; filename={pdf_filename}')
        ])



    

