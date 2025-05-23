$(document).ready(function () {
  // Caminho base das APIs (respeitando Blueprint)
  const API_BASE = '/financeiro/lancamentos/api';

  // Função para formatar valor em moeda brasileira
  function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);
  }

  // Popula select de mês
  for (let m = 1; m <= 12; m++) {
    $('#filtro-mes').append(`<option value="${String(m).padStart(2, '0')}">${String(m).padStart(2, '0')}</option>`);
  }
  // Popula select de ano (exemplo: últimos 4 anos)
  const anoAtual = new Date().getFullYear();
  for (let a = anoAtual; a >= anoAtual - 3; a--) {
    $('#filtro-ano').append(`<option value="${a}">${a}</option>`);
  }
  // Define mês e ano atuais como selecionados
  $('#filtro-mes').val(String(new Date().getMonth() + 1).padStart(2, '0'));
  $('#filtro-ano').val(anoAtual);

  // Função que carrega os cards
  function carregarDados(mes, ano) {
    if (!mes || !ano) {
      const hoje = new Date();
      mes = String(hoje.getMonth() + 1).padStart(2, '0');
      ano = hoje.getFullYear();
    }
    $.ajax({
      url: `${API_BASE}/resumo_contas?mes=${mes}&ano=${ano}`,
      method: 'GET',
      dataType: 'json',
      success: function (data) {
        $('#valor-pendente').text(formatCurrency(data.pendente));
        $('#valor-atrasado').text(formatCurrency(data.atrasado));
        $('#valor-pago').text(formatCurrency(data.pago));
        $('#valor-total').text(formatCurrency(data.total));
        $('#variacao-pendente').text(data.variacao_pendente + '%');
        $('#variacao-atrasado').text(data.variacao_atrasado + '%');
        $('#variacao-pago').text(data.variacao_pago + '%');
        $('#variacao-total').text(data.variacao_total + '%');
      },
      error: function (xhr) {
        console.error('Erro ao carregar resumo:', xhr.responseText);
        $('#valor-pendente,#valor-atrasado,#valor-pago,#valor-total').text('R$ 0,00');
        $('#variacao-pendente,#variacao-atrasado,#variacao-pago,#variacao-total').text('0%');
      }
    });
  }

  // Chama ao abrir a página
  carregarDados($('#filtro-mes').val(), $('#filtro-ano').val());

  // Ao trocar qualquer filtro, atualiza os cards
  $('#filtro-mes, #filtro-ano').change(function () {
    carregarDados($('#filtro-mes').val(), $('#filtro-ano').val());
  });

  // ----------- AUTOCOMPLETE/AUTOPREENCHIMENTO DOS SELECTS DINÂMICOS -----------
  $('.select-dinamico').each(function () {
    const select = $(this);
    const campo = select.data('campo');
    select.empty().append('<option value=""></option>'); // Limpa e mantém a opção vazia

    $.ajax({
      url: `${API_BASE}/opcoes_select?campo=${campo}`,
      type: "GET",
      success: function (data) {
        data.forEach(function (item) {
          if (item && item.trim() !== '') {
            select.append($('<option>', {
              value: item,
              text: item
            }));
          }
        });
        // Aplica select2
        select.select2({
          tags: true,
          placeholder: "Selecione ou digite para criar",
          allowClear: true,
          width: '100%'
        });
      },
      error: function (xhr) {
        console.error(`Erro ao buscar opções para ${campo}:`, xhr.responseText);
        // Mesmo assim aplica select2 para não quebrar a UI
        select.select2({
          tags: true,
          placeholder: "Selecione ou digite para criar",
          allowClear: true,
          width: '100%'
        });
      }
    });
  });

  // ----------- AUTOPREENCHIMENTO AO SELECIONAR PLANO DE CONTAS -----------
  $('select[name="plano_de_contas"]').on('change', function () {
    const plano = $(this).val();
    if (!plano) return;
    $.get(`${API_BASE}/plano_info?plano=${encodeURIComponent(plano)}`, function (data) {
      function preencher(nomeCampo, valor) {
        if (!valor) return;
        const $campo = $(`select[name="${nomeCampo}"]`);
        $campo.val(valor).trigger('change');
        const $container = $campo.next('.select2');
        $container.addClass('auto-preenchido');
        setTimeout(() => $container.removeClass('auto-preenchido'), 1500);
      }
      preencher("fornecedor", data.fornecedor);
      preencher("categorias", data.categorias);
      preencher("tipo_custo", data.tipo_custo);
      preencher("empresa", data.empresa);
      preencher("conta", data.conta);
    });
  });

  // ----------- MOSTRAR/OCULTAR SEÇÕES DO FORMULÁRIO -----------
  $('#pagamento_tipo').on('change', function () {
    const tipo = $(this).val();
    $('#boleto-section, #cartao-section, #pix-section').hide();
    if (tipo === 'Boleto') {
      $('#boleto-section').show();
    } else if (tipo === 'Cartão de Crédito' || tipo === 'Cartão de Débito') {
      $('#cartao-section').show();
    } else if (tipo === 'PIX') {
      $('#pix-section').show();
    }
  });

  // ----------- LÓGICA DE PARCELAS DE BOLETO -----------
  $('#add-installment').on('click', function () {
    const container = $('#installments-container');
    const newRow = $('.installment-row:first').clone();
    newRow.find('input').val('');
    newRow.find('.remove-installment').show().on('click', function () {
      $(this).closest('.installment-row').remove();
      calcularValorTotal();
    });
    container.append(newRow);
    newRow.find('.installment-value').on('change', calcularValorTotal);
  });

  function calcularValorTotal() {
    let total = 0;
    $('.installment-value').each(function () {
      const valor = parseFloat($(this).val()) || 0;
      total += valor;
    });
    $('input[name="valor"]').val(total.toFixed(2));
  }

  $('.installment-value:first').on('change', calcularValorTotal);
  $('.remove-installment:first').on('click', function () {
    $(this).closest('.installment-row').remove();
    calcularValorTotal();
  });

  // ----------- STATUS AUTOMÁTICO -----------
  $('input[name="valor_pago"], input[name="vencimento"]').on('change', function () {
    const valorPago = $('input[name="valor_pago"]').val();
    const vencimento = $('input[name="vencimento"]').val();
    if (valorPago && parseFloat(valorPago) > 0) {
      $('select[name="status"]').val('paid').trigger('change');
    } else if (vencimento) {
      const dataParts = vencimento.split('-');
      if (dataParts.length === 3) {
        const vencDate = new Date(dataParts[0], dataParts[1] - 1, dataParts[2]);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (vencDate < today) {
          $('select[name="status"]').val('overdue').trigger('change');
        } else {
          $('select[name="status"]').val('pending').trigger('change');
        }
      }
    }
  });

  // ----------- ENVIO DO FORMULÁRIO AJAX -----------
  $('#lancamento-form').on('submit', function (e) {
    e.preventDefault();
    const formData = new FormData(this);
    if (!$('input[name="valor"]').val() || !$('input[name="vencimento"]').val()) {
      alert('Valor e vencimento são obrigatórios!');
      return;
    }
    $('.btn-save').html('<i class="bi bi-arrow-repeat spin"></i> Salvando...').prop('disabled', true);
    $.ajax({
      url: `${API_BASE}/salvar_lancamento`,
      method: 'POST',
      data: formData,
      processData: false,
      contentType: false,
      success: function (response) {
        if (response.success) {
          alert('Lançamento salvo com sucesso!');
          $('#lancamento-form')[0].reset();
          carregarDados();
          $('#boleto-section, #cartao-section, #pix-section').hide();
          $('#installments-container').html(`
            <div class="installment-row">
              <input type="date" name="boleto_data[]" placeholder="Data de vencimento" class="installment-date">
              <input type="number" step="0.01" name="boleto_valor[]" placeholder="Valor" class="installment-value">
              <button type="button" class="remove-installment" style="display: none;"><i class="bi bi-trash"></i></button>
            </div>
          `);
        } else {
          alert('Erro ao salvar: ' + (response.error || 'Erro desconhecido'));
        }
      },
      error: function (xhr) {
        alert('Erro na comunicação com o servidor: ' + xhr.responseText);
      },
      complete: function () {
        $('.btn-save').html('<i class="bi bi-check-circle"></i> Salvar').prop('disabled', false);
      }
    });
  });

  // Carrega os dados iniciais ao abrir (só para garantir)
  carregarDados();

  // Adiciona estilo para ícone de loading
  $('<style>.spin {animation: spin 1s linear infinite;} @keyframes spin {100% {transform: rotate(360deg);}}</style>').appendTo('head');
});
