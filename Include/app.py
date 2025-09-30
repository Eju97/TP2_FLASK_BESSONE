import os
from flask import Flask, url_for, redirect, render_template, request, flash, session, make_response
from config import SQLALCHEMY_DATABASE_URI, DevelopmentConfig
from models import db, Usuario, Cliente, Producto, Factura, DetalleFactura
from xhtml2pdf import pisa
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config.from_object(DevelopmentConfig)
db.init_app(app)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash("Por favor, inicie sesion", "warning")
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get("email") ##Se utiliza parentesis porque con corchete da error
        password = request.form['password']
        if Usuario.query.filter_by(username=username).first():
            flash('Nombre de usuario ya registrado', 'danger')
            return redirect(url_for('registrar'))
        if Usuario.query.filter_by(email=email).first():
            flash('El mail ingresado ya se encuentra en uso', 'danger')
            return redirect(url_for('registrar'))

        nuevo_usuario = Usuario(username=username, email=email, rol="usuario")
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Usted se ha registrado', 'success')
        return redirect(url_for('login'))
    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.check_password(password):
            session['user_id'] = usuario.id
            session['username'] = usuario.username
            flash('Se ha iniciado sesion con exito', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Usted Se ha deconectado', 'success')
    return redirect(url_for('login'))

@app.route("/clientes")
def listaDeClientes():
    clientes = Cliente.query.all()
    return render_template("listaClientes.html", clientes=clientes)

@app.route("/clientes/nuevo", methods=["GET", "POST"])
def agregarCliente():
    if request.method == "POST":
        cliente = Cliente(
            nombre=request.form["nombre"],
            direccion=request.form["direccion"],
            telefono=request.form["telefono"],
            email=request.form["email"]
        )
        db.session.add(cliente)
        db.session.commit()
        flash("Cliente registrado")
        return redirect(url_for("listaDeClientes"))
    return render_template("modalCliente.html")

@app.route("/clientes/editar/<int:id_cliente>", methods=["GET", "POST"])
def editarCliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    if request.method == "POST":
        cliente.nombre = request.form["nombre"]
        cliente.direccion = request.form["direccion"]
        cliente.telefono = request.form["telefono"]
        cliente.email = request.form["email"]
        db.session.commit()
        flash("Cliente actualizado")
        return redirect(url_for("listaDeClientes"))
    return render_template("modalCliente.html", cliente=cliente)

@app.route("/clientes/eliminar/<int:id_cliente>")
def eliminarCliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    cliente.esActivo = False #en vez de eliminar al cliente, se deshabilita el mismo dentro de la base de datos, esto con el objetivo de mantener la integridad del sistema, como a su vez mantener el nombre del mismo en las facturas.
    db.session.commit()
    flash("Cliente borrado")
    return redirect(url_for("listaDeClientes"))

@app.route("/productos")
def listaProductos():
    productos = Producto.query.all()
    return render_template("listaProductos.html", productos=productos)

@app.route("/productos/nuevo", methods=["GET", "POST"])
def agregarProducto():
    if request.method == "POST":
        producto = Producto(
            descripcion=request.form["descripcion"],
            precio=request.form["precio"],
            stock=request.form["stock"]
        )
        db.session.add(producto)
        db.session.commit()
        flash("Producto agregado", "error")
        return redirect(url_for("listaProductos"))
    return render_template("modalProducto.html")

@app.route("/productos/editar/<int:id_producto>", methods=["GET", "POST"])
def editarProducto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    if request.method == "POST":
        producto.descripcion = request.form["descripcion"]
        producto.precio = request.form["precio"]
        producto.stock = request.form["stock"]
        db.session.commit()
        flash("Producto actualizado")
        return redirect(url_for("listaProductos"))
    return render_template("modalProducto.html", producto=producto)

@app.route("/productos/eliminar/<int:id_producto>")
def eliminarProducto(id_producto):
    producto = Producto.query.get_or_404(id_producto)
    db.session.delete(producto)
    db.session.commit()
    flash("Producto borrado")
    return redirect(url_for("listaProductos"))



@app.route("/facturas", methods=["GET", "POST"])
def listaFacturas():
    clientes = Cliente.query.all()
    facturas = Factura.query.all()

    cliente = None
    if request.method == "POST":
        id_cliente = request.form.get("id_cliente")
        if id_cliente:
            facturas = Factura.query.filter_by(id_cliente=id_cliente).all()
            cliente = db.session.get(Cliente, id_cliente)

    return render_template("listaFacturas.html", facturas=facturas, clientes=clientes, cliente=cliente)


@app.route("/facturas/nuevo", methods=["GET", "POST"])
def nuevaFactura():
    clientes = Cliente.query.all()
    productos = Producto.query.all()
    if request.method == "POST":
        id_cliente = request.form["id_cliente"]
        observaciones = request.form.get("observaciones")
        productos_seleccionados = request.form.getlist("productos[]")
        cantidades = request.form.getlist("cantidades[]")
        factura = Factura(id_cliente=id_cliente, total=0, observaciones=observaciones)
        db.session.add(factura)
        db.session.flush()
        total = 0
        for i, id_producto in enumerate(productos_seleccionados):
            producto = db.session.get(Producto, int(id_producto))
            cantidad = int(cantidades[i])
            subtotal = producto.precio * cantidad
            detalle = DetalleFactura(
                id_factura=factura.id_factura,
                id_producto=producto.id_producto,
                cantidad=cantidad,
                precio_unitario=producto.precio,
                subtotal=subtotal
            )
            total += subtotal
            db.session.add(detalle)
            producto.stock -= cantidad
        factura.total = total
        db.session.commit()
        flash("Factura creada con éxito", "success")
        return redirect(url_for("listaFacturas"))
    return render_template("modalFactura.html", clientes=clientes, productos=productos)


@app.route("/facturas/<int:id_factura>")
def detalle_factura(id_factura):
    factura = Factura.query.get_or_404(id_factura)
    detalles = factura.detalles
    return render_template("detalleFactura.html", factura=factura, detalles=detalles)


@app.route("/facturas/<int:id_factura>/pdf")
def factura_pdf(id_factura):
    factura = Factura.query.get_or_404(id_factura)
    detalles = factura.detalles
    html = render_template("facturaPdf.html", factura=factura, detalles=detalles)
    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)
    response = make_response(pdf_bytes.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=factura_{id_factura}.pdf"
    return response


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)