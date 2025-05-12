// ==================== INICIALIZAÇÃO DO FORMULÁRIO ====================
$(document).ready(function() {
  // Configura todos os selects dinâmicos com Select2
  $('.select-dinamico').select2({
    tags: true,
    placeholder: "Selecione ou digite para criar",
    width: '100%'
  }).on('select2:select', function(e) {
    // Quando uma nova opção é criada (tag)
    if (e.params.data.tag) {
      const campo = $(this).data('campo');
      const valor = e.params.data.text;

      // Envia a nova opção para o servidor
      fetch('/api/adicionar_opcao', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ campo, valor })
      }).then(r => r.json()).then(data => {
        if (!data.success) {
          console.error("Erro ao salvar:", data.error);
          $(this).val(null).trigger('change');
        }
      });
    }
  });

  // ==================== MANIPULAÇÃO DE DATAS ====================
  // Formata data para o padrão do seu DB (DD/MM/YYYY)
  $('input[type="date"]').on('change', function() {
    const date = new Date(this.value);
    if (!isNaN(date.getTime())) {
      const day = date.getDate().toString().padStart(2, '0');
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      this.value = `${day}/${month}/${date.getFullYear()}`;
    }
  });

  // ==================== LÓGICA DE STATUS ====================
  // Atualiza status quando valor pago ou vencimento mudar
  $('input[name="valor_pago"], input[name="vencimento"]').on('change', function() {
    const valorPago = $('input[name="valor_pago"]').val();
    const vencimento = $('input[name="vencimento"]').val();

    // Se tem valor pago, marca como "Pago"
    if (valorPago && parseFloat(valorPago) > 0) {
      $('select[name="status"]').val('paid').trigger('change');
    }
    // Se não tem valor pago mas tem vencimento, verifica status
    else if (vencimento) {
      const [day, month, year] = vencimento.split('/');
      const vencDate = new Date(year, month - 1, day);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      // Verifica se está atrasado
      if (vencDate < today) {
        $('select[name="status"]').val('overdue').trigger('change');
      } else {
        $('select[name="status"]').val('pending').trigger('change');
      }
    }
  });
});
$(document).ready(function() {
    // Configuração dos selects dinâmicos
    $('.select-dinamico').select2({
        tags: true,
        placeholder: "Selecione ou digite para criar",
        width: '100%'
    });

    // Botão "+" para adicionar novas opções
    $('.select-dinamico').next('.select2').find('.select2-selection').append(
        '<button type="button" class="btn-adicionar" title="Adicionar novo item">+</button>'
    );

    // Modal para adicionar novas opções
    const modal = $('#modalAdicionar');
    $('.btn-adicionar').click(function() {
        const selectId = $(this).closest('.select2').prev('.select-dinamico').attr('id');
        modal.data('campo', selectId).show();
    });

    $('.close, #btnConfirmar').click(function() {
        const campo = modal.data('campo');
        const novoValor = $('#novoValor').val();

        if (novoValor && $(this).is('#btnConfirmar')) {
            // Adiciona ao Select2
            const novoOption = new Option(novoValor, novoValor, true, true);
            $(`#${campo}`).append(novoOption).trigger('change');

            // Envia para o backend (via AJAX)
            $.post('/api/adicionar-opcao', {
                campo: campo,
                valor: novoValor
            }, function(response) {
                if (!response.success) {
                    alert('Erro ao salvar: ' + response.error);
                }
            });
        }

        $('#novoValor').val('');
        modal.hide();
    });
});
$(document).ready(function() {
    // Configuração dos selects com criação inline
    $('.select-criavel').each(function() {
        const select = $(this);

        // Transforma em Select2 com tags
        select.select2({
            tags: true,
            placeholder: "Selecione ou digite para criar",
            width: '100%',
            createTag: function(params) {
                return {
                    id: params.term,
                    text: params.term,
                    newOption: true
                };
            }
        });

        // Adiciona o botão "+" dentro do próprio select
        select.next('.select2').find('.select2-selection').append(
            '<button type="button" class="btn-add-option" title="Adicionar item">+</button>'
        );

        // Lógica para adicionar novos itens
        select.on('select2:select', function(e) {
            if (e.params.data.newOption) {
                const novoValor = e.params.data.text;
                const campo = select.data('campo');

                // Envia para o backend
                $.post('/api/adicionar-opcao', {
                    campo: campo,
                    valor: novoValor
                }, function(response) {
                    if (!response.success) {
                        console.error("Erro ao salvar:", response.error);
                        select.val(null).trigger('change');
                    }
                });
            }
        });
    });

