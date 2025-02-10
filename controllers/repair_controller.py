from odoo import http
from odoo.http import request
import logging


class RepairController(http.Controller):

    _logger = logging.getLogger(__name__)

    @http.route('/repairstatus/<int:tech_repair_id>', type='http', auth="public", website=True)
    def tech_repair_status(self, tech_repair_id, **kwargs):
        # Forzo Odoo a usare un db
        db_name = request.httprequest.args.get('db')
        if db_name:
            request.session.db = db_name
        tech_repair_order = request.env['tech.repair.order'].sudo().browse(tech_repair_id)

        if not tech_repair_order.exists():
            return request.render('tech_repair_management.tech_repair_not_found', {})

        # Filtra solo i messaggi destinati al cliente
        chat_messages = request.env['tech.repair.chat.message'].sudo().search([
            ('tech_repair_order_id', '=', tech_repair_id),
        ], order='create_date asc')

        # Log per debug
        self._logger.info("Messaggi trovati per la riparazione %s: %s", tech_repair_id, chat_messages)


        return request.render('tech_repair_management.tech_repair_status_page', {
            'repair': tech_repair_order,
            'customer_state': tech_repair_order.customer_state_id.name if tech_repair_order.customer_state_id else "Stato non ancora disponibile",
            'chat_messages': chat_messages
        })

    @http.route('/repairstatus/send_message', type='http', auth="public", methods=['POST'], website=True)
    def send_message(self, **post):
        tech_repair_id = post.get('tech_repair_id')
        customer_message = post.get('customer_message')  # 🛠️ Nome corretto del campo dal form

        if tech_repair_id and customer_message:
            tech_repair_order = request.env['tech.repair.order'].sudo().browse(int(tech_repair_id))
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

                self._logger.info("Messaggio ricevuto dal cliente per riparazione %s: %s", tech_repair_id, customer_message)

        return request.redirect(f'/repairstatus/{tech_repair_id}')
    

