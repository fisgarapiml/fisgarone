<?php
/**
 * Script de Geração de NFe - Sistema Fisgarone
 * Integração com SEFAZ-SP usando NFePHP
 */

require_once 'vendor/autoload.php';

use NFePHP\NFe\Tools;
use NFePHP\NFe\Make;
use NFePHP\Common\Certificate;
use NFePHP\NFe\Complements;

try {
    echo "[4/5] NFe-TESTE: Gerando XML...\n";
    echo "   → Schema: NFe v4.00.\n";
    
    // Configuração
    $config = include 'config.php';
    
    // Certificado A1 (simulado - em produção usar arquivo real)
    $certificado = file_get_contents('certificado_dummy.pfx'); // Arquivo do certificado
    $senha = '1qaz2wsx';
    
    // Simulação - em produção usar certificado real
    // $certificate = Certificate::readPfx($certificado, $senha);
    $certificate = null; // Simulação
    $tools = new Tools(json_encode($config), $certificate);
    $tools->model('55'); // Modelo NFe
    
    // Criando NFe
    $nfe = new Make();
    
    // Dados da NFe
    $std = new stdClass();
    $std->versao = '4.00';
    $std->Id = null;
    $std->pk_nItem = null;
    
    // Identificação da NFe
    $std = new stdClass();
    $std->cUF = 35; // São Paulo
    $std->cNF = '12345678';
    $std->natOp = 'Venda de mercadoria';
    $std->mod = 55;
    $std->serie = 1;
    $std->nNF = 1;
    $std->dhEmi = date('Y-m-d\TH:i:sP');
    $std->dhSaiEnt = null;
    $std->tpNF = 1; // Saída
    $std->idDest = 1; // Operação interna
    $std->cMunFG = 3550308; // São Paulo
    $std->tpImp = 1; // Retrato
    $std->tpEmis = 1; // Normal
    $std->cDV = null;
    $std->tpAmb = 1; // Produção
    $std->finNFe = 1; // Normal
    $std->indFinal = 1; // Consumidor final
    $std->indPres = 1; // Presencial
    $std->procEmi = 0; // Aplicativo do contribuinte
    $std->verProc = '1.0.0';
    
    $nfe->taginfNFe($std);
    
    // Emitente
    $std = new stdClass();
    $std->xNome = "FISGARONE LTDA";
    $std->xFant = "FISGARONE";
    $std->IE = "123456789012";
    $std->IEST = null;
    $std->IM = null;
    $std->CNAE = "4751201";
    $std->CRT = 3; // Regime Normal
    
    $nfe->tagemit($std);
    
    // Endereço do emitente
    $std = new stdClass();
    $std->xLgr = "RUA EXEMPLO";
    $std->nro = "123";
    $std->xCpl = null;
    $std->xBairro = "CENTRO";
    $std->cMun = 3550308;
    $std->xMun = "SAO PAULO";
    $std->UF = "SP";
    $std->CEP = "01234567";
    $std->cPais = 1058;
    $std->xPais = "BRASIL";
    $std->fone = "1112345678";
    
    $nfe->tagenderEmit($std);
    
    // Destinatário
    $std = new stdClass();
    $std->xNome = "CONSUMIDOR FINAL";
    $std->indIEDest = 9; // Não contribuinte
    $std->CPF = "12345678909";
    $std->idEstrangeiro = null;
    
    $nfe->tagdest($std);
    
    // Endereço do destinatário
    $std = new stdClass();
    $std->xLgr = "RUA DO CLIENTE";
    $std->nro = "456";
    $std->xCpl = null;
    $std->xBairro = "VILA EXEMPLO";
    $std->cMun = 3550308;
    $std->xMun = "SAO PAULO";
    $std->UF = "SP";
    $std->CEP = "01234567";
    $std->cPais = 1058;
    $std->xPais = "BRASIL";
    $std->fone = null;
    
    $nfe->tagenderDest($std);
    
    echo "   → Emitente: FISGARONE LTDA (IE: 123456789012).\n";
    echo "   → Destinatário: CPF 123.456.789-09.\n";
    
    // Produto
    $std = new stdClass();
    $std->item = 1;
    $std->cProd = "1001";
    $std->cEAN = null;
    $std->xProd = "Notebook Gamer Ultimate";
    $std->NCM = "84713021";
    $std->EXTIPI = null;
    $std->CFOP = "5102";
    $std->uCom = "UN";
    $std->qCom = 1;
    $std->vUnCom = 5299.00;
    $std->vProd = 5299.00;
    $std->cEANTrib = null;
    $std->uTrib = "UN";
    $std->qTrib = 1;
    $std->vUnTrib = 5299.00;
    $std->vFrete = null;
    $std->vSeg = null;
    $std->vDesc = null;
    $std->vOutro = null;
    $std->indTot = 1;
    $std->xPed = null;
    $std->nItemPed = null;
    $std->nFCI = null;
    
    $nfe->tagprod($std);
    
    echo "   → Produto: Notebook Gamer Ultimate (NCM 8471.30, R$ 5.299,00).\n";
    
    // Imposto
    $std = new stdClass();
    $std->item = 1;
    $std->vTotTrib = 0.00;
    
    $nfe->tagimposto($std);
    
    // ICMS
    $std = new stdClass();
    $std->item = 1;
    $std->orig = 0;
    $std->CST = '00';
    $std->modBC = 3;
    $std->vBC = 5299.00;
    $std->pICMS = 18.00;
    $std->vICMS = 953.82;
    
    $nfe->tagICMS($std);
    
    // PIS
    $std = new stdClass();
    $std->item = 1;
    $std->CST = '01';
    $std->vBC = 5299.00;
    $std->pPIS = 1.65;
    $std->vPIS = 87.43;
    
    $nfe->tagPIS($std);
    
    // COFINS
    $std = new stdClass();
    $std->item = 1;
    $std->CST = '01';
    $std->vBC = 5299.00;
    $std->pCOFINS = 7.60;
    $std->vCOFINS = 402.72;
    
    $nfe->tagCOFINS($std);
    
    // Total
    $std = new stdClass();
    $std->vBC = 5299.00;
    $std->vICMS = 953.82;
    $std->vICMSDeson = 0.00;
    $std->vFCPUFDest = 0.00;
    $std->vICMSUFDest = 0.00;
    $std->vICMSUFRemet = 0.00;
    $std->vFCP = 0.00;
    $std->vBCST = 0.00;
    $std->vST = 0.00;
    $std->vFCPST = 0.00;
    $std->vFCPSTRet = 0.00;
    $std->vProd = 5299.00;
    $std->vFrete = 0.00;
    $std->vSeg = 0.00;
    $std->vDesc = 0.00;
    $std->vII = 0.00;
    $std->vIPI = 0.00;
    $std->vIPIDevol = 0.00;
    $std->vPIS = 87.43;
    $std->vCOFINS = 402.72;
    $std->vOutro = 0.00;
    $std->vNF = 5299.00;
    $std->vTotTrib = 1443.97;
    
    $nfe->tagICMSTot($std);
    
    // Transporte
    $std = new stdClass();
    $std->modFrete = 9; // Sem frete
    
    $nfe->tagtransp($std);
    
    // Pagamento
    $std = new stdClass();
    $std->vTroco = null;
    
    $nfe->tagpag($std);
    
    $std = new stdClass();
    $std->indPag = 0; // À vista
    $std->tPag = '01'; // Dinheiro
    $std->vPag = 5299.00;
    $std->CNPJ = null;
    $std->tBand = null;
    $std->cAut = null;
    $std->tpIntegra = null;
    
    $nfe->tagdetPag($std);
    
    // Informações adicionais
    $std = new stdClass();
    $std->infAdFisco = null;
    $std->infCpl = "NFe gerada pelo sistema FISGARONE - Integração MANUS";
    
    $nfe->taginfAdic($std);
    
    // Gerar XML
    $xml = $nfe->getXML();
    
    echo "\n[5/5] VALIDAÇÃO:\n";
    echo "   → XSD: ";
    
    // Validar XML
    $valid = $tools->validarXml($xml);
    if ($valid) {
        echo "OK.\n";
    } else {
        echo "ERRO.\n";
        throw new Exception("XML inválido");
    }
    
    echo "   → Assinatura: ";
    
    // Assinar XML
    $xmlAssinado = $tools->signNFe($xml);
    
    if ($xmlAssinado) {
        echo "OK.\n";
        
        // Salvar XML
        file_put_contents('nfe_teste.xml', $xmlAssinado);
        
        echo "\n[SUCESSO] XML gerado e validado com sucesso.\n";
        echo "   → Arquivo: nfe_teste.xml\n";
        echo "   → Tamanho: " . strlen($xmlAssinado) . " bytes\n";
        
        return $xmlAssinado;
    } else {
        echo "ERRO.\n";
        throw new Exception("Erro na assinatura");
    }
    
} catch (Exception $e) {
    echo "\n[ERRO] " . $e->getMessage() . "\n";
    exit(1);
}
?>

