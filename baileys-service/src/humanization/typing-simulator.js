"use strict";
/**
 * Typing Simulator - Simula comportamento humano de digitação no WhatsApp
 *
 * Inclui:
 * - "composing" (digitando...)
 * - "paused" (pausou)
 * - "recording" (gravando áudio - futuro)
 * - Timing realista com muitas variações
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TypingSimulator = void 0;
const human_timing_1 = require("./human-timing");
/**
 * Simulador de digitação humana
 */
class TypingSimulator {
    constructor(socket, tenantId, chipId, timingProfile) {
        this.socket = socket;
        this.tenantId = tenantId;
        this.chipId = chipId;
        this.timing = new human_timing_1.HumanTiming(tenantId, chipId, timingProfile);
    }
    /**
     * Envia mensagem com simulação de digitação humana
     */
    async sendMessageHumanLike(jid, text, options = {}) {
        const startTime = Date.now();
        const result = {
            success: false,
            totalDuration: 0,
            stages: {}
        };
        // Opções padrão
        const opts = {
            showTyping: true,
            simulatePauses: true,
            pauseProbability: 0.3,
            reviewBeforeSend: true,
            stayOnlineAfter: false,
            ...options
        };
        try {
            console.log(`[TypingSimulator] ${this.chipId.substring(0, 8)} → ${jid} ` +
                `| Texto: "${text.substring(0, 30)}${text.length > 30 ? '...' : ''}" ` +
                `(${text.length} chars)`);
            // ========== ETAPA 1: PENSAR ==========
            const thinkingDelay = this.timing.getThinkingDelay();
            result.stages.thinking = thinkingDelay;
            console.log(`[TypingSimulator] 💭 Pensando por ${thinkingDelay}ms...`);
            await this.timing.sleep(thinkingDelay);
            // ========== ETAPA 2: COMEÇAR A DIGITAR ==========
            if (opts.showTyping) {
                try {
                    await this.socket.sendPresenceUpdate('composing', jid);
                    console.log(`[TypingSimulator] ⌨️  Presence: composing`);
                }
                catch (error) {
                    console.warn(`[TypingSimulator] ⚠️ Erro ao enviar composing:`, error);
                }
            }
            // ========== ETAPA 3: SIMULAR DIGITAÇÃO COM PAUSAS ==========
            const typingDelay = this.timing.getTypingDelay(text.length);
            result.stages.typing = typingDelay;
            result.stages.pauses = [];
            if (opts.simulatePauses && text.length > 20) {
                // Dividir tempo de digitação em chunks com pausas
                const chunks = this.splitTypingIntoChunks(text, opts.pauseProbability);
                console.log(`[TypingSimulator] 📝 Digitando em ${chunks.length} chunks com pausas...`);
                for (let i = 0; i < chunks.length; i++) {
                    const chunk = chunks[i];
                    // Digitar chunk
                    await this.timing.sleep(chunk.duration);
                    // Fazer pausa se não for último chunk
                    if (i < chunks.length - 1 && chunk.pause) {
                        const pauseDuration = this.timing.randomDelay({ min: 500, max: 2000 });
                        result.stages.pauses.push(pauseDuration);
                        console.log(`[TypingSimulator] ⏸️  Pausa ${i + 1}: ${pauseDuration}ms`);
                        // Enviar "paused" durante pausa (opcional, mais realista)
                        if (opts.showTyping && Math.random() < 0.5) {
                            try {
                                await this.socket.sendPresenceUpdate('paused', jid);
                                console.log(`[TypingSimulator] ⏸️  Presence: paused`);
                            }
                            catch (error) {
                                console.warn(`[TypingSimulator] ⚠️ Erro ao enviar paused:`, error);
                            }
                        }
                        await this.timing.sleep(pauseDuration);
                        // Voltar a "composing" após pausa
                        if (opts.showTyping && Math.random() < 0.5) {
                            try {
                                await this.socket.sendPresenceUpdate('composing', jid);
                                console.log(`[TypingSimulator] ⌨️  Presence: composing (retomada)`);
                            }
                            catch (error) {
                                console.warn(`[TypingSimulator] ⚠️ Erro ao enviar composing:`, error);
                            }
                        }
                    }
                }
            }
            else {
                // Digitação contínua sem pausas
                console.log(`[TypingSimulator] 📝 Digitando continuamente por ${typingDelay}ms...`);
                await this.timing.sleep(typingDelay);
            }
            // ========== ETAPA 4: REVISAR ==========
            if (opts.reviewBeforeSend) {
                // Parar de digitar
                if (opts.showTyping) {
                    try {
                        await this.socket.sendPresenceUpdate('paused', jid);
                        console.log(`[TypingSimulator] ✅ Presence: paused (revisão)`);
                    }
                    catch (error) {
                        console.warn(`[TypingSimulator] ⚠️ Erro ao enviar paused:`, error);
                    }
                }
                const reviewDelay = this.timing.getReviewDelay();
                result.stages.review = reviewDelay;
                console.log(`[TypingSimulator] 👀 Revisando por ${reviewDelay}ms...`);
                await this.timing.sleep(reviewDelay);
            }
            // ========== ETAPA 5: ENVIAR MENSAGEM ==========
            const sendStart = Date.now();
            console.log(`[TypingSimulator] 📤 Enviando mensagem...`);
            await this.socket.sendMessage(jid, { text });
            const sendDuration = Date.now() - sendStart;
            result.stages.sending = sendDuration;
            console.log(`[TypingSimulator] ✅ Mensagem enviada (${sendDuration}ms)`);
            // ========== ETAPA 6: PRESENCE PÓS-ENVIO ==========
            if (opts.stayOnlineAfter) {
                try {
                    await this.socket.sendPresenceUpdate('available', jid);
                    console.log(`[TypingSimulator] 🟢 Presence: available`);
                    // Ficar online por um tempo aleatório
                    const onlineDelay = this.timing.getOnlinePresenceDelay();
                    console.log(`[TypingSimulator] 🕐 Ficando online por ${(onlineDelay / 60000).toFixed(1)}min...`);
                    // Não aguardar (não bloquear) - apenas agendar
                    setTimeout(async () => {
                        try {
                            await this.socket.sendPresenceUpdate('unavailable');
                            console.log(`[TypingSimulator] ⚫ Presence: unavailable (auto)`);
                        }
                        catch (error) {
                            console.warn(`[TypingSimulator] ⚠️ Erro ao enviar unavailable:`, error);
                        }
                    }, onlineDelay);
                }
                catch (error) {
                    console.warn(`[TypingSimulator] ⚠️ Erro ao gerenciar presence:`, error);
                }
            }
            else {
                // Voltar para disponível imediatamente
                try {
                    await this.socket.sendPresenceUpdate('available', jid);
                    console.log(`[TypingSimulator] 🟢 Presence: available`);
                }
                catch (error) {
                    console.warn(`[TypingSimulator] ⚠️ Erro ao enviar available:`, error);
                }
            }
            // ========== RESULTADO ==========
            result.success = true;
            result.totalDuration = Date.now() - startTime;
            console.log(`[TypingSimulator] ✅ SUCESSO | Duração total: ${result.totalDuration}ms ` +
                `(${(result.totalDuration / 1000).toFixed(1)}s)`);
            return result;
        }
        catch (error) {
            result.success = false;
            result.error = error instanceof Error ? error.message : String(error);
            result.totalDuration = Date.now() - startTime;
            console.error(`[TypingSimulator] ❌ ERRO após ${result.totalDuration}ms:`, error);
            return result;
        }
    }
    /**
     * Divide digitação em chunks com pausas
     */
    splitTypingIntoChunks(text, pauseProbability) {
        const chunks = [];
        // Dividir texto em palavras
        const words = text.split(/\s+/);
        const totalWords = words.length;
        // Agrupar em chunks de 3-7 palavras
        let currentChunkWords = 0;
        const wordsPerChunk = Math.floor(Math.random() * 5) + 3; // 3-7
        for (let i = 0; i < totalWords; i++) {
            currentChunkWords++;
            // Fim do chunk ou fim do texto
            if (currentChunkWords >= wordsPerChunk || i === totalWords - 1) {
                const chunkLength = currentChunkWords * 5; // média 5 chars/palavra
                const duration = this.timing.getTypingDelay(chunkLength);
                const shouldPause = Math.random() < pauseProbability;
                chunks.push({ duration, pause: shouldPause });
                currentChunkWords = 0;
            }
        }
        return chunks;
    }
    /**
     * Envia múltiplas mensagens com delays entre elas (anti-burst)
     */
    async sendMultipleMessages(jid, messages, options) {
        const results = [];
        console.log(`[TypingSimulator] 📨 Enviando ${messages.length} mensagens para ${jid}`);
        for (let i = 0; i < messages.length; i++) {
            const message = messages[i];
            console.log(`[TypingSimulator] 📬 Mensagem ${i + 1}/${messages.length}`);
            // Enviar mensagem com simulação
            const result = await this.sendMessageHumanLike(jid, message, options);
            results.push(result);
            // Delay entre mensagens (exceto após última)
            if (i < messages.length - 1) {
                const betweenDelay = this.timing.getBetweenMessagesDelay();
                console.log(`[TypingSimulator] ⏳ Aguardando ${betweenDelay}ms antes da próxima mensagem...`);
                await this.timing.sleep(betweenDelay);
            }
        }
        const totalDuration = results.reduce((sum, r) => sum + r.totalDuration, 0);
        const successCount = results.filter(r => r.success).length;
        console.log(`[TypingSimulator] ✅ Concluído | ${successCount}/${messages.length} enviadas | ` +
            `Tempo total: ${(totalDuration / 1000).toFixed(1)}s`);
        return results;
    }
    /**
     * Simula leitura de mensagens recebidas
     */
    async simulateReadingMessages(messages) {
        console.log(`[TypingSimulator] 📖 Simulando leitura de ${messages.length} mensagens`);
        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            const textLength = msg.text?.length || 50;
            // Delay proporcional ao tamanho da mensagem
            const readDelay = this.timing.getReadMessageDelay();
            const lengthFactor = Math.min(textLength / 50, 3); // max 3x
            const totalDelay = Math.round(readDelay * lengthFactor);
            console.log(`[TypingSimulator] 👀 Lendo mensagem ${i + 1}/${messages.length} ` +
                `(${textLength} chars) por ${totalDelay}ms...`);
            await this.timing.sleep(totalDelay);
            // Marcar como lida
            try {
                await this.socket.readMessages([msg.key]);
                console.log(`[TypingSimulator] ✅ Mensagem marcada como lida`);
            }
            catch (error) {
                console.warn(`[TypingSimulator] ⚠️ Erro ao marcar como lida:`, error);
            }
            // Delay entre leituras
            if (i < messages.length - 1) {
                const betweenDelay = this.timing.getBetweenActionsDelay();
                await this.timing.sleep(betweenDelay);
            }
        }
    }
    /**
     * Simula visualização de status
     */
    async simulateViewingStatus(statusCount = 1) {
        console.log(`[TypingSimulator] 📸 Simulando visualização de ${statusCount} status`);
        for (let i = 0; i < statusCount; i++) {
            const viewDelay = this.timing.randomDelay({ min: 3000, max: 8000 });
            console.log(`[TypingSimulator] 👁️  Vendo status ${i + 1}/${statusCount} por ${viewDelay}ms...`);
            await this.timing.sleep(viewDelay);
            // Delay entre status
            if (i < statusCount - 1) {
                const betweenDelay = this.timing.getBetweenActionsDelay();
                await this.timing.sleep(betweenDelay);
            }
        }
    }
    /**
     * Troca perfil de timing
     */
    changeTimingProfile(profileName) {
        this.timing.changeProfile(profileName);
    }
    /**
     * Retorna timing instance (para uso avançado)
     */
    getTiming() {
        return this.timing;
    }
}
exports.TypingSimulator = TypingSimulator;
exports.default = TypingSimulator;
