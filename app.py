import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from dotenv import load_dotenv 

#Cargar las variables de entorno
load_dotenv()

#crear instancia
app =  Flask(__name__)

# Configuración de la base de datos PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
#app.config['SQLALCHEMY_DATABASE_URI'] = "URL EXTERNA RENDER"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

#Modelo de la base de datos
class Estudiante(db.Model):
    __tablename__ = 'estudiantes'
    no_control = db.Column(db.String, primary_key=True)
    nombre = db.Column(db.String)
    ap_paterno = db.Column(db.String)
    ap_materno = db.Column(db.String)
    semestre = db.Column(db.Integer)

#endpoint para obtener todos los estudiantes
@app.route('/estudiantes', methods=['GET'])
def get_estudiantes():
    estudiantes = Estudiante.query.all()
    lista_estudiantes = []
    for estudiante in estudiantes:
        lista_estudiantes.append({
            'no_control ': estudiante.no_control,
            'nombre ': estudiante.nombre,
            'ap_paterno ': estudiante.ap_paterno,
            'ap_materno ': estudiante.ap_materno,
            'semestre ': estudiante.semestre
        })
    return jsonify(lista_estudiantes)
    
#endpoint para obtener un estudiante por el no_control
@app.route('/estudiantes/<no_control>', methods=['GET'])
def get_estudiante(no_control):
    estudiante = Estudiante.query.get(no_control)
    if estudiante is None:
        return jsonify ({'msg':'Estudiante no encontrado'})
    return jsonify({
        'no_control': estudiante.no_control,
        'nombre': estudiante.nombre,
        'ap_paterno': estudiante.ap_paterno,
        'ap_materno': estudiante.ap_materno,
        'semestre': estudiante.semestre,
    })


#endpoint para agregar un nuevo alumno
@app.route('/estudiantes', methods=['POST'])
def insert_estudiante():
    # 1) Content-Type y parseo
    if not request.is_json:
        return json_error('El cuerpo debe ser JSON (Content-Type: application/json).', status=415)
    data = request.get_json(silent=True) or {}

    # 2) Validación de campos requeridos
    requeridos = {'no_control','nombre','ap_paterno','ap_materno','semestre'}
    faltantes = [k for k in requeridos if k not in data or str(data[k]).strip() == '']
    if faltantes:
        return json_error(f'Campos requeridos faltantes: {", ".join(sorted(faltantes))}.', status=400)

    # 3) Normalización y tipos
    no_control = str(data['no_control']).strip()
    nombre = str(data['nombre']).strip()
    ap_paterno = str(data['ap_paterno']).strip()
    ap_materno = str(data['ap_materno']).strip()
    semestre = str(data['semestre']).strip()


    # 4) Pre-chequeos de duplicados (evita golpear el constraint)
    if Estudiante.query.get(no_control):
        return json_error('Ya existe un estudiante con ese no_control.', status=409)

    if Estudiante.query.filter_by(
        nombre=nombre, ap_paterno=ap_paterno, ap_materno=ap_materno
    ).first():
        return json_error('Ya existe un estudiante con el mismo nombre completo.', status=409)

    # 5) Intento de inserción
    nuevo_estudiante = Estudiante(
        no_control=no_control,
        nombre=nombre,
        ap_paterno=ap_paterno,
        ap_materno=ap_materno,
        semestre=semestre
    )

    try:
        db.session.add(nuevo_estudiante)
        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        # Intenta inferir el constraint que falló
        msg = (str(e.orig) or '').lower()
        if 'uq_estudiante_nombre_completo' in msg or ('unique' in msg and 'nombre' in msg):
            return json_error('Ya existe un estudiante con el mismo nombre completo.', status=409)
        if 'primary key' in msg or 'duplicate key value' in msg or 'no_control' in msg:
            return json_error('Ya existe un estudiante con ese no_control.', status=409)
        return json_error('Conflicto de integridad al guardar el estudiante.', status=409)

    except SQLAlchemyError as e:
        db.session.rollback()
        return json_error('Error de base de datos al guardar el estudiante.', status=500)

    except Exception as e:
        db.session.rollback()
        return json_error('Error inesperado al guardar el estudiante.', status=500)

    # 6) Respuesta de éxito
    resp = jsonify({
        'message': 'Estudiante agregado exitosamente',
        'estudiante': nuevo_estudiante.to_dict()
    })
    resp.status_code = 201
    resp.headers['Location'] = url_for('get_estudiante', no_control=no_control, _external=True)
    return resp

#endpoint para eliminar un estudiante
@app.route('/estudiantes/<no_control>', methods=['DELETE'])
def delete_estudiante(no_control):
    estudiante = Estudiante.query.get(no_control)
    if estudiante is None:
        return jsonify({'msg': 'Estudiante no encontrado'})
    db.session.delete(estudiante)
    db.session.commit()
    return jsonify({'msg': 'Estudiante eliminado correctamente'})


#endpoint para actualizar un estudiante
@app.route('/estudiantes/<no_control>', methods=['PATCH'])
def updateestudiante(no_control):
    estudiante = Estudiante.query.get(no_control)
    if estudiante is None:
        return jsonify({'msg': 'Estudiante no encontrado'})
    data = request.get_json()

    if "nombre" in data:
        estudiante.nombre = data['nombre']
    if "ap_paterno" in data:
        estudiante.ap_paterno = data['ap_paterno']
    if "ap_materno" in data:
        estudiante.ap_materno = data['ap_materno']
    if "semestre" in data:
        estudiante.semestre = data['semestre']

    db.session.commit()
    return jsonify({'msg': 'Estudiante actualizado correctamente'})


if __name__ == '__main__':
    app.run(debug=True)