"""
Aplicação Flask para o Frontend do Sistema de Detecção de Veículos de Emergência
"""

from flask import (
    Flask, render_template, render_template_string,
    request, redirect, url_for, session, jsonify,
    send_file, Response, stream_with_context
)
import requests
import os
from dotenv import load_dotenv
import io
import time

load_dotenv()
from datetime import datetime, timedelta
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# =====================================================================
# CONFIGURAÇÃO DA API BACKEND
# =====================================================================
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000/api/v1')
API_TIMEOUT = 30  # segundos


# =====================================================================
# FUNÇÕES DE AUTENTICAÇÃO E UTILITÁRIOS
# =====================================================================

def get_auth_header():
    token = session.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def api_call(method, endpoint, data=None, files=None, params=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_auth_header()
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=API_TIMEOUT)
        elif method == 'POST':
            if files:
                # Para upload de arquivos, não definir Content-Type - requests fará automaticamente
                headers.pop('Content-Type', None)
                response = requests.post(url, headers=headers, files=files, data=data, timeout=API_TIMEOUT)
            else:
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        elif method == 'PUT':
            headers['Content-Type'] = 'application/json'
            response = requests.put(url, headers=headers, json=data, timeout=API_TIMEOUT)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=API_TIMEOUT)
        else:
            return False, {'error': 'Método HTTP inválido'}, 400

        try:
            response_data = response.json()
        except Exception:
            response_data = {'message': response.text}

        return response.status_code < 400, response_data, response.status_code

    except requests.exceptions.RequestException as e:
        return False, {'error': str(e)}, 500


# =====================================================================
# ROTAS DE AUTENTICAÇÃO
# =====================================================================

@app.route('/')
def index():
    if 'access_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return render_template('auth/login.html', error='Email e senha são obrigatórios')
        success, data, _ = api_call('POST', '/auth/login', {'email': email, 'password': password})
        if success:
            session['access_token'] = data.get('access_token')
            session['user_email'] = email
            session['user_role'] = data.get('role', 'operator')
            return redirect(url_for('dashboard'))
        else:
            return render_template('auth/login.html', error=data.get('detail', 'Erro no login'))
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================================================================
# ROTAS DE DASHBOARD
# =====================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_email=session.get('user_email'))


# =====================================================================
# CRUD DE FUNCIONÁRIOS (USUÁRIOS)
# =====================================================================

@app.route('/employees', methods=['GET'])
@login_required
def list_employees():
    success, data, _ = api_call('GET', '/employees')
    employees = data if success and isinstance(data, list) else (data.get('items', []) if isinstance(data, dict) else [])
    return render_template('employees/list.html', employees=employees)

@app.route('/employees/<employee_id>', methods=['GET'])
@login_required
def employee_detail(employee_id):
    success, data, _ = api_call('GET', f'/employees/{employee_id}')
    if not success:
        return render_template('error.html', error='Funcionário não encontrado'), 404
    return render_template('employees/detail.html', employee=data)

@app.route('/employees/new', methods=['GET', 'POST'], endpoint='new_employee')
@login_required
def new_employee():
    if request.method == 'GET':
        return render_template('employees/edit.html', employee={}, is_create=True)
    payload = {
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "role": request.form.get("role", "operator"),
        "password": request.form.get("password"),
    }
    
    payload = {k: v for k, v in payload.items() if v is not None and v != ""}
    
    success, data, status_code = api_call('POST', '/employees', payload)
    
    if not success:
        error_message = data.get('message', 'Erro ao criar funcionário') if isinstance(data, dict) else data
        return render_template('employees/edit.html', 
                             employee=payload, 
                             is_create=True, 
                             error=error_message)
    
    return redirect(url_for('list_employees'))

@app.route('/employees/<employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if request.method == 'GET':
        success, data, _ = api_call('GET', f'/employees/{employee_id}')
        if not success:
            return render_template('error.html', error='Funcionário não encontrado'), 404
        return render_template('employees/edit.html', employee=data, is_create=False)

    payload = {
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "role": request.form.get("role"),
        "password": request.form.get("password"),
    }
    payload = {k: v for k, v in payload.items() if v is not None and v != ""}
    success, data, _ = api_call('PUT', f'/employees/{employee_id}', payload)
    if not success:
        return render_template('employees/edit.html', employee=payload, is_create=False, error=data)
    return redirect(url_for('employee_detail', employee_id=employee_id))

@app.route('/employees/<employee_id>/delete', methods=['POST'])
@login_required
def delete_employee(employee_id):
    api_call('DELETE', f'/employees/{employee_id}')
    return redirect(url_for('list_employees'))


# =====================================================================
# ROTAS DE DETECÇÃO DE IMAGEM
# =====================================================================

@app.route('/detections/image', methods=['GET', 'POST'])
@login_required
def detect_image():
    if request.method == 'GET':
        return render_template('detections/image_upload.html')
    
    if 'file' not in request.files:
        return render_template('detections/image_upload.html', error='Nenhum arquivo selecionado')
    
    file = request.files['file']
    if file.filename == '':
        return render_template('detections/image_upload.html', error='Nenhum arquivo selecionado')
    
    if not file.content_type.startswith('image/'):
        return render_template('detections/image_upload.html', error='Arquivo deve ser uma imagem')
    
    source_id = request.form.get('source_id', 'uploaded_image')
    
    url = f"{API_BASE_URL}/detections/image"
    headers = get_auth_header()
    
    try:
        file.stream.seek(0)
        files = {'file': (file.filename, file.stream, file.content_type)}
        data = {'source_id': source_id}
        
        response = requests.post(
            url, 
            headers=headers, 
            files=files, 
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            detections = response.json()
            print("=== ESTRUTURA DOS DADOS RECEBIDOS ===")
            for i, detection in enumerate(detections):
                print(f"Detecção {i}:")
                for key, value in detection.items():
                    print(f"  {key}: {value} ({type(value)})")
            print("=====================================")
            
            if isinstance(detections, list):
                return render_template('detections/image_results.html', detections=detections)
            else:
                return render_template('detections/image_upload.html', error='Resposta inválida da API')
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_detail = error_data.get('detail', f'Erro {response.status_code} ao processar imagem')
            return render_template('detections/image_upload.html', error=error_detail)
            
    except requests.exceptions.RequestException as e:
        return render_template('detections/image_upload.html', error=f'Erro de conexão: {str(e)}')
    except Exception as e:
        return render_template('detections/image_upload.html', error=f'Erro interno: {str(e)}')

@app.route('/detections/image/<detection_id>/annotated')
@login_required
def get_annotated_image(detection_id):
    """Serve a imagem anotada com as detecções"""
    url = f"{API_BASE_URL}/detections/image/annotated/{detection_id}"
    headers = get_auth_header()
    
    try:
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT, stream=True)
        
        if response.status_code == 200:
            return response.content, 200, {
                'Content-Type': response.headers.get('Content-Type', 'image/jpeg'),
                'Content-Disposition': response.headers.get('Content-Disposition', 'inline')
            }
        else:
            return "Imagem não encontrada", 404
            
    except requests.exceptions.RequestException:
        return "Erro ao buscar imagem", 500


# =====================================================================
# ROTAS DE DETECÇÃO DE VÍDEO
# =====================================================================

@app.route('/detections/video', methods=['GET', 'POST'])
@login_required
def detect_video():
    """Upload e processamento de vídeo"""
    if request.method == 'GET':
        return render_template('detections/video_upload.html')
    
    if 'file' not in request.files:
        return render_template('detections/video_upload.html', error='Nenhum arquivo selecionado')
    
    file = request.files['file']
    if file.filename == '':
        return render_template('detections/video_upload.html', error='Nenhum arquivo selecionado')
    
    if not file.content_type.startswith('video/'):
        return render_template('detections/video_upload.html', error='Arquivo deve ser um vídeo')
    
    source_id = request.form.get('source_id', 'uploaded_video')
    
    # Fazer upload diretamente para a API
    url = f"{API_BASE_URL}/detections/video"
    headers = get_auth_header()
    
    try:
        file.stream.seek(0)
        files = {'file': (file.filename, file.stream, file.content_type)}
        data = {'source_id': source_id}
        
        response = requests.post(
            url, 
            headers=headers, 
            files=files, 
            data=data,
            timeout=120
        )
        
        if response.status_code == 200:
            job_data = response.json()
            return jsonify({'job_id': job_data['job_id']}), 200
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_detail = error_data.get('detail', f'Erro {response.status_code} ao processar vídeo')
            return render_template('detections/video_upload.html', error=error_detail)
            
    except requests.exceptions.RequestException as e:
        return render_template('detections/video_upload.html', error=f'Erro de conexão: {str(e)}')
    except Exception as e:
        return render_template('detections/video_upload.html', error=f'Erro interno: {str(e)}')

@app.route('/detections/video/<job_id>')
@login_required
def video_status(job_id):
    """Página de status do processamento de vídeo"""
    try:
        success, job_data, status_code = api_call('GET', f'/detections/video/{job_id}')
        
        if not success:
            if status_code == 404:
                return render_template('error.html', error=f'Job {job_id} não encontrado'), 404
            else:
                error_msg = job_data.get('detail', 'Erro desconhecido') if isinstance(job_data, dict) else str(job_data)
                return render_template('error.html', error=f'Erro ao buscar job: {error_msg}'), 500

        if job_data.get('status') != 'completed':
            return render_template('detections/video_status.html', 
                                   job=job_data, 
                                   not_ready_message="O vídeo ainda está sendo processado. Por favor, verifique a lista de jobs para acompanhar o status.")

        return render_template('detections/video_status.html', job=job_data)                        
    except Exception as e:
        print(f"❌ Erro em video_status: {str(e)}")
        return render_template('error.html', error=f'Erro interno: {str(e)}'), 500

@app.route('/detections/video/<job_id>/annotated')
@login_required
def get_annotated_video(job_id):
    """Serve o vídeo anotado com as detecções - PROXY STREAMING"""
    try:
        url = f"{API_BASE_URL}/detections/video/annotated/{job_id}"
        headers = get_auth_header()

        backend_resp = requests.get(url, headers=headers, timeout=API_TIMEOUT, stream=True)

        if backend_resp.status_code != 200:
            return "Vídeo anotado não encontrado ou não processado", backend_resp.status_code

        def generate():
            for chunk in backend_resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        response = Response(
            stream_with_context(generate()),
            mimetype='video/mp4',
        )

        content_length = backend_resp.headers.get('Content-Length')
        if content_length:
            response.headers['Content-Length'] = content_length

        response.headers['Content-Disposition'] = f'inline; filename=annotated_video_{job_id}.mp4'
        response.headers['Accept-Ranges'] = 'bytes'

        return response

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição ao proxy de vídeo: {str(e)}")
        return "Erro ao buscar vídeo via API", 500
    except Exception as e:
        print(f"❌ Erro interno no proxy de vídeo: {str(e)}")
        return "Erro interno", 500


@app.route('/detections/image/<detection_id>')
@login_required
def get_detection_image(detection_id):
    """Serve a imagem de uma detecção específica"""
    success, detection, _ = api_call('GET', f'/detections/{detection_id}')
    
    if not success or not detection.get('media_reference'):
        return "Imagem não encontrada", 404
    
    image_path = detection.get('media_reference')
    
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    else:
        url = f"{API_BASE_URL}/detections/image/annotated/{detection_id}"
        headers = get_auth_header()
        
        try:
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT, stream=True)
            if response.status_code == 200:
                image_data = io.BytesIO(response.content)
                return send_file(
                    image_data,
                    mimetype=response.headers.get('Content-Type', 'image/jpeg')
                )
            else:
                return "Imagem não encontrada", 404
        except requests.exceptions.RequestException:
            return "Erro ao buscar imagem", 500

@app.route('/api/detections/video/<job_id>/status')
@login_required
def api_video_status(job_id):
    """API endpoint para verificar status do job"""
    try:
        success, job_data, status_code = api_call('GET', f'/detections/video/{job_id}')
        
        if success:
            return jsonify(job_data)
        else:
            return jsonify({'error': 'Job não encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Erro em api_video_status: {str(e)}")
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/api/detections/video/<job_id>/wait-completion')
@login_required
def api_wait_video_completion(job_id):
    """API endpoint para aguardar conclusão do processamento"""
    max_wait_time = 300  # 5 minutos máximo
    check_interval = 5   # Verificar a cada 5 segundos
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        success, job_data, status_code = api_call('GET', f'/detections/video/{job_id}')
        
        if not success:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        status = job_data.get('status')
        
        if status == 'completed':
            return jsonify({
                'status': 'completed',
                'job': job_data,
                'message': 'Processamento concluído'
            })
        elif status == 'failed':
            return jsonify({
                'status': 'failed', 
                'job': job_data,
                'error': job_data.get('error_message', 'Erro desconhecido')
            }), 400
        
        time.sleep(check_interval)
    
    return jsonify({
        'status': 'timeout',
        'message': 'Tempo máximo de espera excedido'
    }), 408

@app.route('/detections/images')
@login_required
def list_image_detections():
    success, data, _ = api_call('GET', '/detections/images')
    detections = data if success and isinstance(data, list) else []
    
    message = request.args.get('message')
    
    return render_template('detections/images_list.html', detections=detections, message=message)


@app.route('/detections/video/jobs')
@login_required
def video_jobs_list():
    """Lista todos os jobs de vídeo processados"""
    success, jobs_data, status_code = api_call('GET', '/detections/jobs')
    
    jobs = []
    if success and isinstance(jobs_data, list):
        jobs = jobs_data
    
    message = request.args.get('message')
    return render_template('detections/video_jobs_list.html', jobs=jobs, message=message)

# =====================================================================
# ROTAS DE RELATÓRIOS
# =====================================================================

@app.route('/reports')
@login_required
def reports_dashboard():
    """Dashboard principal de relatórios"""
    stats = {
        'total_detections': 0,
        'ambulance_count': 0,
        'police_car_count': 0,
        'fire_truck_count': 0
    }
    
    success, detections_data, _ = api_call('GET', '/detections')
    if success and isinstance(detections_data, list):
        stats['total_detections'] = len(detections_data)
        
        for detection in detections_data:
            vehicle_type = detection.get('vehicle_type', '')
            if vehicle_type == 'ambulance':
                stats['ambulance_count'] += 1
            elif vehicle_type == 'police_car':
                stats['police_car_count'] += 1
            elif vehicle_type == 'fire_truck':
                stats['fire_truck_count'] += 1
    
    return render_template('reports/dashboard.html', stats=stats)

@app.route('/reports/detections', methods=['GET', 'POST'])
@login_required
def detections_report():
    """Relatório de estatísticas de detecções"""
    vehicle_types = ['ambulance', 'police_car', 'fire_truck', 'traffic_enforcement']
    
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        vehicle_type = request.form.get('vehicle_type')
        
        if vehicle_type == 'all':
            vehicle_type = None
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=7)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        start_iso = start_dt.isoformat() + '+00:00'
        end_iso = end_dt.isoformat() + '+00:00'
        
        params = {
            'start_date': start_iso,
            'end_date': end_iso
        }
        if vehicle_type:
            params['vehicle_type'] = vehicle_type
            
        success, data, status_code = api_call('GET', '/reports/detections', params=params)
        
        if success:
            return render_template('reports/detections_report.html', 
                                 report_data=data,
                                 vehicle_types=vehicle_types,
                                 filters={
                                     'start_date': start_date,
                                     'end_date': end_date,
                                     'vehicle_type': vehicle_type
                                 })
        else:
            error_msg = data.get('detail', 'Erro ao gerar relatório')
            return render_template('reports/detections_report.html',
                                 error=error_msg,
                                 vehicle_types=vehicle_types)
    
    return render_template('reports/detections_report.html', vehicle_types=vehicle_types)

@app.route('/reports/traffic', methods=['GET', 'POST'])
@login_required
def traffic_report():
    """Relatório de tráfego por hora"""
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=1)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        start_iso = start_dt.isoformat() + '+00:00'
        end_iso = end_dt.isoformat() + '+00:00'
        
        params = {
            'start_date': start_iso,
            'end_date': end_iso
        }
            
        success, data, status_code = api_call('GET', '/reports/traffic', params=params)
        
        if success:
            return render_template('reports/traffic_report.html', 
                                 report_data=data,
                                 filters={
                                     'start_date': start_date,
                                     'end_date': end_date
                                 })
        else:
            error_msg = data.get('detail', 'Erro ao gerar relatório')
            return render_template('reports/traffic_report.html', error=error_msg)
    
    return render_template('reports/traffic_report.html')

@app.route('/reports/vehicle-activity', methods=['GET', 'POST'])
@login_required
def vehicle_activity_report():
    """Relatório de atividade por tipo de veículo"""
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        group_by = request.form.get('group_by', 'day')
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=7)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        start_iso = start_dt.isoformat() + '+00:00'
        end_iso = end_dt.isoformat() + '+00:00'
        
        params = {
            'start_date': start_iso,
            'end_date': end_iso,
            'group_by': group_by
        }
            
        success, data, status_code = api_call('GET', '/reports/vehicle-activity', params=params)
        
        if success:
            return render_template('reports/vehicle_activity_report.html', 
                                 report_data=data,
                                 filters={
                                     'start_date': start_date,
                                     'end_date': end_date,
                                     'group_by': group_by
                                 })
        else:
            error_msg = data.get('detail', 'Erro ao gerar relatório')
            return render_template('reports/vehicle_activity_report.html', error=error_msg)
    
    return render_template('reports/vehicle_activity_report.html')

@app.route('/reports/siren-usage', methods=['GET', 'POST'])
@login_required
def siren_usage_report():
    """Relatório de uso de sirene"""
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=7)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        mock_data = {
            "total_detections": 150,
            "siren_on": 89,
            "siren_off": 61,
            "siren_usage_rate": 59.3,
            "by_vehicle_type": {
                "fire_truck": {"total": 45, "siren_on": 35, "rate": 77.8},
                "police_car": {"total": 67, "siren_on": 42, "rate": 62.7},
                "ambulance": {"total": 38, "siren_on": 12, "rate": 31.6}
            }
        }
        
        return render_template('reports/siren_usage_report.html', 
                             report_data=mock_data,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date
                             })
    
    return render_template('reports/siren_usage_report.html')

@app.route('/reports/confidence', methods=['GET', 'POST'])
@login_required
def confidence_report():
    """Relatório de confiança das detecções"""
    vehicle_types = ['ambulance', 'police_car', 'fire_truck', 'traffic_enforcement']
    
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        vehicle_type = request.form.get('vehicle_type', 'all')
        
        if vehicle_type == 'all':
            vehicle_type_param = None
        else:
            vehicle_type_param = vehicle_type
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=7)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
        start_iso = start_dt.isoformat() + '+00:00'
        end_iso = end_dt.isoformat() + '+00:00'
        
        params = {
            'start_date': start_iso,
            'end_date': end_iso
        }
        if vehicle_type_param:
            params['vehicle_type'] = vehicle_type_param
            
        success, data, status_code = api_call('GET', '/reports/confidence', params=params)
        
        if success:
            return render_template('reports/confidence_report.html', 
                                 report_data=data,
                                 vehicle_types=vehicle_types,
                                 filters={
                                     'start_date': start_date,
                                     'end_date': end_date,
                                     'vehicle_type': vehicle_type
                                 })
        else:
            error_msg = data.get('detail', 'Erro ao gerar relatório')
            return render_template('reports/confidence_report.html', 
                                 error=error_msg,
                                 vehicle_types=vehicle_types)
    
    return render_template('reports/confidence_report.html', vehicle_types=vehicle_types)

@app.route('/reports/performance', methods=['GET', 'POST'])
@login_required
def performance_report():
    """Relatório de performance do sistema"""
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        start_dt = datetime.fromisoformat(start_date) if start_date else datetime.now() - timedelta(days=30)
        end_dt = datetime.fromisoformat(end_date) if end_date else datetime.now()
        
        mock_data = {
            "total_processed": 1247,
            "average_processing_time": 1.23,
            "peak_hours": ["08:00", "14:00", "18:00"],
            "system_uptime": 99.8
        }
        
        return render_template('reports/performance_report.html', 
                             report_data=mock_data,
                             filters={
                                 'start_date': start_date,
                                 'end_date': end_date
                             })
    
    return render_template('reports/performance_report.html')


# =====================================================================
# FILTROS DE TEMPLATE
# =====================================================================

@app.template_filter('format_number')
def format_number(value):
    """Filtro para formatar números com separadores de milhar"""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


# =====================================================================
# TRATAMENTO DE ERROS
# =====================================================================

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error='Página não encontrada'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Erro interno do servidor'), 500


# =====================================================================
# CONTEXT PROCESSORS
# =====================================================================

@app.context_processor
def inject_user():
    return {
        'user_email': session.get('user_email'),
        'user_role': session.get('user_role'),
        'is_authenticated': 'access_token' in session
    }


# =====================================================================
# INICIALIZAÇÃO
# =====================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
