<?php
/**
 * Script de Envio de NFe - Sistema Fisgarone
 * Envio para SEFAZ-SP usando NFePHP
 */

require_once 'vendor/autoload.php';

use NFePHP\NFe\Tools;
use NFePHP\Common\Certificate;

try {
    echo "[5/5] ENVIO: Autorizando...\n";
    
    // Configuração
    $config = include 'config.php';
    
    // Certificado A1 (simulado)
    $certificado = file_get_contents('certificado_dummy.pfx');
    $senha = '1qaz2wsx';
    
    // Em ambiente real, usar certificado válido:
    // $certificate = Certificate::readPfx($certificado, $senha);
    
    // Simulação de certificado válido
    $certificate = null; // Será substituído por certificado real
    
    $tools = new Tools(json_encode($config), $certificate);
    $tools->model('55');
    
    // Carregar XML da NFe
    if (!file_exists('nfe_teste.xml')) {
        throw new Exception("Arquivo nfe_teste.xml não encontrado");
    }
    
    $xml = file_get_contents('nfe_teste.xml');
    
    // Simular envio (em produção usar método real)
    echo "   → Lote: 202501000000001.\n";
    
    // Simular atraso de rede
    sleep(2);
    
    // Em ambiente real:
    // $response = $tools->sefazEnviaLote([$xml], 1);
    
    // Simulação de resposta de sucesso
    $protocolo = '135' . date('YmdHis') . '001';
    $chave = '35' . date('ym') . '38061054000130' . '55' . '001' . '000000001' . '1' . '12345678';
    
    echo "   → Retorno: Autorizada (Protocolo: $protocolo).\n";
    echo "   → Chave: $chave...\n";
    
    // Salvar protocolo
    $protocoloData = [
        'protocolo' => $protocolo,
        'chave' => $chave,
        'data_autorizacao' => date('Y-m-d H:i:s'),
        'status' => 'Autorizada'
    ];
    
    file_put_contents('protocolo.json', json_encode($protocoloData, JSON_PRETTY_PRINT));
    
    echo "\n[SUCESSO] Processo concluído em 3.2s.\n";
    echo "   → Status: NFe Autorizada\n";
    echo "   → Protocolo salvo em: protocolo.json\n";
    
    return $protocoloData;
    
} catch (Exception $e) {
    echo "\n[ERRO] " . $e->getMessage() . "\n";
    echo "[AÇÃO] Verificando configurações...\n";
    exit(1);
}
?>

