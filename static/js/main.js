/**
 * Script principal para o Sistema de Detecção de Veículos de Emergência
 */

// Função para validar formulários
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    return form.checkValidity() === false ? false : true;
}

// Função para mostrar/esconder senha
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Função para confirmar ações
function confirmAction(message) {
    return confirm(message || 'Tem certeza que deseja continuar?');
}

// Função para fazer requisições AJAX
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição:', error);
        throw error;
    }
}

// Função para atualizar o status de um vídeo
async function checkVideoStatus(jobId) {
    try {
        const data = await fetchAPI(`/api/detections/video/${jobId}/status`);
        return data;
    } catch (error) {
        console.error('Erro ao verificar status:', error);
        return null;
    }
}

// Função para formatar datas
function formatDate(dateString) {
    const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('pt-BR', options);
}

// Função para formatar percentual
function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}

// Inicialização quando o DOM está pronto
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar validação de formulários
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Adicionar comportamento para botões de confirmação
    const deleteButtons = document.querySelectorAll('button[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirmAction(this.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });
});

// Função para atualizar a página periodicamente
function autoRefresh(interval = 5000) {
    setInterval(() => {
        location.reload();
    }, interval);
}

// Função para exibir notificações
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.style.maxWidth = '400px';
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Função para desabilitar botão durante envio
function disableSubmitButton(formId) {
    const form = document.getElementById(formId);
    if (form) {
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Processando...';
        }
    }
}

// Exportar funções para uso global
window.validateForm = validateForm;
window.togglePasswordVisibility = togglePasswordVisibility;
window.confirmAction = confirmAction;
window.fetchAPI = fetchAPI;
window.checkVideoStatus = checkVideoStatus;
window.formatDate = formatDate;
window.formatPercent = formatPercent;
window.autoRefresh = autoRefresh;
window.showNotification = showNotification;
window.disableSubmitButton = disableSubmitButton;

