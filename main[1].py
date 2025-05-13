from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from io import BytesIO
from xhtml2pdf import pisa

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ddt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    piva = db.Column(db.String(20), nullable=False)
    indirizzo = db.Column(db.String(200))

class DDT(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, default=datetime.utcnow)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    cliente = db.relationship('Cliente')
    totale = db.Column(db.Float)
    iva = db.Column(db.Float)
    totale_ivato = db.Column(db.Float)

class RigaDDT(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ddt_id = db.Column(db.Integer, db.ForeignKey('ddt.id'), nullable=False)
    descrizione = db.Column(db.String(200))
    kg = db.Column(db.Float)
    colli = db.Column(db.Integer)
    prezzo_unitario = db.Column(db.Float)
    totale_riga = db.Column(db.Float)

@app.route('/')
def index():
    return redirect(url_for('lista_ddt'))

@app.route('/clienti')
def lista_clienti():
    clienti = Cliente.query.all()
    return render_template('clienti.html', clienti=clienti)

@app.route('/clienti/aggiungi', methods=['GET', 'POST'])
def aggiungi_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        piva = request.form['piva']
        indirizzo = request.form['indirizzo']
        nuovo_cliente = Cliente(nome=nome, piva=piva, indirizzo=indirizzo)
        db.session.add(nuovo_cliente)
        db.session.commit()
        return redirect(url_for('lista_clienti'))
    return render_template('aggiungi_cliente.html')

@app.route('/ddt')
def lista_ddt():
    ddts = DDT.query.all()
    return render_template('ddt.html', ddts=ddts)

@app.route('/ddt/nuovo', methods=['GET', 'POST'])
def nuovo_ddt():
    clienti = Cliente.query.all()
    if request.method == 'POST':
        cliente_id = request.form['cliente']
        descrizioni = request.form.getlist('descrizione')
        kgs = request.form.getlist('kg')
        colli = request.form.getlist('colli')
        prezzi = request.form.getlist('prezzo')

        numero = (db.session.query(db.func.max(DDT.numero)).scalar() or 0) + 1
        nuovo_ddt = DDT(numero=numero, cliente_id=cliente_id)
        db.session.add(nuovo_ddt)
        db.session.commit()

        totale = 0
        for desc, kg, col, prezzo in zip(descrizioni, kgs, colli, prezzi):
            kg = float(kg)
            col = int(col)
            prezzo = float(prezzo)
            totale_riga = kg * prezzo
            riga = RigaDDT(ddt_id=nuovo_ddt.id, descrizione=desc, kg=kg, colli=col, prezzo_unitario=prezzo, totale_riga=totale_riga)
            db.session.add(riga)
            totale += totale_riga

        iva = round(totale * 0.22, 2)
        totale_ivato = totale + iva
        nuovo_ddt.totale = totale
        nuovo_ddt.iva = iva
        nuovo_ddt.totale_ivato = totale_ivato
        db.session.commit()

        return redirect(url_for('lista_ddt'))
    return render_template('nuovo_ddt.html', clienti=clienti)

@app.route('/ddt/<int:ddt_id>/stampa')
def stampa_ddt(ddt_id):
    ddt = DDT.query.get_or_404(ddt_id)
    righe = RigaDDT.query.filter_by(ddt_id=ddt_id).all()
    html = render_template('stampa_ddt.html', ddt=ddt, righe=righe)
    response = BytesIO()
    pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=response)
    response.seek(0)
    return make_response(response.read(), 200, {'Content-Type': 'application/pdf', 'Content-Disposition': f'inline; filename=ddt_{ddt.numero}.pdf'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
