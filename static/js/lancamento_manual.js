// ==================== INICIALIZAÇÃO DO FORMULÁRIO ====================
$(document).ready(function() {
  // Configuração responsiva dos selects dinâmicos
  function initializeSelects() {
    $('.select-dinamico, .select-criavel').select2({
      tags: true,
      placeholder: "Selecione ou digite",
      width: '100%',
      dropdownAutoWidth: true,
      dropdownParent: $(window).width() < 768 ? $('body') : null,
      createTag: function(params) {
        return {
          id: params.term,
          text: params.term,
          newOption: true
        };
      }
    });

    // Ajuste para mobile - fecha o teclado virtual após seleção
    if ($(window).width() < 768) {
      $('.select2-selection').on('touchstart', function() {
        $(this).blur();
      });
    }
  }

  // Inicializa os selects
  initializeSelects();

  // Re-inicializa os selects quando a janela é redimensionada
  $(window).on('resize', function() {
    $('.select-dinamico, .select-criavel').select2('destroy');
    initializeSelects();
  });

  // ==================== MANIPULAÇÃO DE DATAS (MOBILE-FRIENDLY) ====================
  $('input[type="date"]').on('change', function() {
    if ($(window).width() < 768) {
      // Formato simplificado para mobile
      const date = new Date(this.value);
      if (!isNaN(date.getTime())) {
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        $(this).val(`${day}/${month}/${date.getFullYear()}`);
      }
    }
  });

  // ==================== LÓGICA DE STATUS ====================
  function updateStatus() {
    const valorPago = parseFloat($('input[name="valor_pago"]').val()) || 0;
    const vencimento = $('input[name="vencimento"]').val();
    const statusSelect = $('select[name="status"]');

    if (valorPago > 0) {
      statusSelect.val('paid').trigger('change');
      return;
    }

    if (vencimento) {
      const [day, month, year] = vencimento.split('/');
      const vencDate = new Date(year, month - 1, day);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      statusSelect.val(vencDate < today ? 'overdue' : 'pending').trigger('change');
    }
  }

  // Eventos para atualização de status
  $('input[name="valor_pago"], input[name="vencimento"]').on('change', updateStatus);

  // ==================== BOTÕES PARA ADICIONAR OPÇÕES ====================
  function setupAddOptionButtons() {
    // Remove botões existentes para evitar duplicação
    $('.btn-adicionar, .btn-add-option').remove();

    // Adiciona botões apenas em telas maiores
    if ($(window).width() >= 768) {
      $('.select-dinamico').next('.select2').find('.select2-selection').append(
        '<button type="button" class="btn-adicionar" title="Adicionar novo item">+</button>'
      );

      $('.btn-adicionar').click(function(e) {
        e.stopPropagation();
        const select = $(this).closest('.select2').prev('.select-dinamico');
        select.select2('open');
      });
    }
  }

  // Configura os botões inicialmente e no redimensionamento
  setupAddOptionButtons();
  $(window).on('resize', setupAddOptionButtons);

  // ==================== TRATAMENTO DE NOVAS OPÇÕES ====================
  $('.select-dinamico, .select-criavel').on('select2:select', function(e) {
    if (e.params.data.newOption) {
      const novoValor = e.params.data.text;
      const campo = $(this).data('campo') || $(this).attr('name');

      // Feedback visual para mobile
      if ($(window).width() < 768) {
        $(this).select2('close');
      }

      // Envia a nova opção para o servidor
      fetch('/api/adicionar_opcao', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ campo, valor: novoValor })
      }).then(r => r.json()).then(data => {
        if (!data.success) {
          console.error("Erro ao salvar:", data.error);
          $(this).val(null).trigger('change');

          // Feedback visual para o usuário
          if ($(window).width() < 768) {
            alert('Não foi possível adicionar o novo item');
          }
        }
      }).catch(error => {
        console.error("Erro na requisição:", error);
        $(this).val(null).trigger('change');
      });
    }
  });
});

// ==================== MODAL PARA ADIÇÃO DE OPÇÕES (MOBILE) ====================
$(document).ready(function() {
  const modal = $('#modalAdicionar');

  // Mostra modal apenas em mobile
  $(document).on('click', '.select2-selection', function() {
    if ($(window).width() < 768) {
      const select = $(this).closest('.select2').prev('.select-dinamico');
      const campo = select.attr('id') || select.data('campo');

      modal.data('campo', campo).show();
      return false; // Evita abrir o select2 padrão
    }
  });

  $('.close, #btnConfirmar').click(function() {
    if ($(this).is('#btnConfirmar')) {
      const campo = modal.data('campo');
      const novoValor = $('#novoValor').val().trim();

      if (novoValor) {
        const select = $(`#${campo}`) || $(`[data-campo="${campo}"]`);

        // Adiciona a nova opção
        const novoOption = new Option(novoValor, novoValor, true, true);
        select.append(novoOption).trigger('change');

        // Envia para o backend
        $.post('/api/adicionar-opcao', {
          campo: campo,
          valor: novoValor
        }).fail(function() {
          select.val(null).trigger('change');
          alert('Erro ao salvar o novo item');
        });
      }
    }

    $('#novoValor').val('');
    modal.hide();
  });
});