/* ============================================================
   EyeGuard — dashboard_avanzado.js
   MediaPipe Face Mesh + Chart.js + fetch a Django
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ─────────────────────────────────────
     CONFIGURACIÓN DE DETECCIÓN
  ───────────────────────────────────── */
  const EAR_UMBRAL      = 0.30;   // EAR < 0.30 = ojos entrecerrados (más sensible)
  const EAR_FRAMES_MIN  = 48;     // ~0.5 seg a 30fps
  const BLINK_UMBRAL    = 20;      // 3 parpadeos acumulados ya dispara
  const COOLDOWN_MS     = 30000;  // 15 seg entre alertas

  // Índices MediaPipe Face Mesh para EAR
  // Ojo izquierdo: puntos verticales y horizontal
  const OJO_IZQ = { A:[159,145], B:[160,144], C:[33,133] };
  // Ojo derecho
  const OJO_DER = { A:[386,374], B:[385,373], C:[362,263] };

  /* ─────────────────────────────────────
     ESTADO
  ───────────────────────────────────── */
  const sesionActiva = document.getElementById('sesionActiva')?.value === '1';
  const csrf         = document.getElementById('csrfToken')?.value || '';
  const urlFatiga    = document.getElementById('registrarFatigaUrl')?.value || '';

  let earFramesBajo   = 0;
  let parpadeos       = 0;       // acumulador del minuto actual
  let parpadeosPorMin = 0;       // valor mostrado (del minuto anterior)
  let ojoCerradoPrev  = false;
  let ultimaAlerta    = 0;
  let tiempoInicio    = Date.now();
  let enviandoFatiga  = false;   // evitar doble envío

  /* ─────────────────────────────────────
     ELEMENTOS DOM
  ───────────────────────────────────── */
  const videoEl        = document.getElementById('videoEl');
  const canvasEl       = document.getElementById('canvasEl');
  const cameraOverlay  = document.getElementById('cameraOverlay');
  const earDisplay     = document.getElementById('earDisplay');
  const earBar         = document.getElementById('earBar');
  const metricEAR      = document.getElementById('metricEAR');
  const metricBlink    = document.getElementById('metricBlink');
  const metricAlertas  = document.getElementById('metricAlertas');
  const metricTiempo   = document.getElementById('metricTiempo');

  /* ─────────────────────────────────────
     TIMER DE SESIÓN
  ───────────────────────────────────── */
  if (sesionActiva) {
    setInterval(() => {
      const diff = Math.floor((Date.now() - tiempoInicio) / 1000);
      const min  = Math.floor(diff / 60).toString().padStart(2, '0');
      const seg  = (diff % 60).toString().padStart(2, '0');
      if (metricTiempo) metricTiempo.textContent = `${min}:${seg}`;
    }, 1000);
  }

  /* ─────────────────────────────────────
     RESET DE PARPADEOS CADA 60 SEG
  ───────────────────────────────────── */
  setInterval(() => {
    parpadeosPorMin = parpadeos;
    parpadeos       = 0;
  }, 60000);

  /* ─────────────────────────────────────
     VISIBILITYCHANGE — cuando el usuario
     vuelve a la pestaña, reiniciar estado
     de detección para que no quede colgado
  ───────────────────────────────────── */
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      // Reiniciar contadores de detección
      earFramesBajo  = 0;
      ojoCerradoPrev = false;
      console.log('[EyeGuard] Ventana activa — detección reiniciada.');
    } else {
      // Página oculta — pausar detección para no acumular frames falsos
      earFramesBajo  = 0;
      ojoCerradoPrev = false;
      console.log('[EyeGuard] Ventana oculta — detección pausada.');
    }
  });

  /* ─────────────────────────────────────
     CHART.JS — EAR en tiempo real
  ───────────────────────────────────── */
  const earCtx = document.getElementById('earChart')?.getContext('2d');
  let earChart  = null;

  if (earCtx) {
    earChart = new Chart(earCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'EAR',
            data: [],
            borderColor: '#818cf8',
            backgroundColor: 'rgba(129,140,248,.1)',
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 0,
            fill: true,
          },
          {
            label: 'Umbral',
            data: [],
            borderColor: '#f87171',
            borderWidth: 1.5,
            borderDash: [6, 3],
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        animation:  false,
        responsive: true,
        plugins:    { legend: { display: false } },
        scales: {
          x: { display: false },
          y: {
            min: 0, max: 0.5,
            grid:  { color: 'rgba(255,255,255,.05)' },
            ticks: { color: '#6b85a8', font: { size: 11 } },
          },
        },
      },
    });
  }

  function actualizarChart(ear) {
    if (!earChart) return;
    const ahora = new Date().toLocaleTimeString('es-EC', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
    earChart.data.labels.push(ahora);
    earChart.data.datasets[0].data.push(parseFloat(ear.toFixed(3)));
    earChart.data.datasets[1].data.push(EAR_UMBRAL);
    if (earChart.data.labels.length > 60) {
      earChart.data.labels.shift();
      earChart.data.datasets[0].data.shift();
      earChart.data.datasets[1].data.shift();
    }
    earChart.update('none');
  }

  /* ─────────────────────────────────────
     CHART.JS — Barras de estadísticas
  ───────────────────────────────────── */
  const statsCtx = document.getElementById('statsChart')?.getContext('2d');
  if (statsCtx) {
    new Chart(statsCtx, {
      type: 'bar',
      data: {
        labels: ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'],
        datasets: [{
          label: 'Alertas',
          data: [0,0,0,0,0,0,0],
          backgroundColor: 'rgba(129,140,248,.35)',
          borderColor: '#818cf8',
          borderWidth: 1.5,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid:{display:false}, ticks:{color:'#6b85a8',font:{size:10}} },
          y: { grid:{color:'rgba(255,255,255,.04)'}, ticks:{color:'#6b85a8',font:{size:10}} },
        },
      },
    });
  }

  /* ─────────────────────────────────────
     CÁLCULO EAR
     EAR = (||p1-p2|| + ||p3-p4||) / (2 * ||p5-p6||)
  ───────────────────────────────────── */
  function dist(a, b) {
    return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
  }

  function calcEAR(lm, ojo) {
    const A = dist(lm[ojo.A[0]], lm[ojo.A[1]]);
    const B = dist(lm[ojo.B[0]], lm[ojo.B[1]]);
    const C = dist(lm[ojo.C[0]], lm[ojo.C[1]]);
    return (A + B) / (2.0 * C);
  }

  /* ─────────────────────────────────────
     MEDIAPIPE — inicializar
  ───────────────────────────────────── */
  if (sesionActiva) {

    if (cameraOverlay) cameraOverlay.classList.add('hidden');

    // Verificar que FaceMesh esté disponible
    if (typeof FaceMesh === 'undefined') {
      console.error('MediaPipe FaceMesh no cargó correctamente.');
      return;
    }

    const faceMesh = new FaceMesh({
      locateFile: (file) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`,
    });

    faceMesh.setOptions({
      maxNumFaces:            1,
      refineLandmarks:        true,
      minDetectionConfidence: 0.6,
      minTrackingConfidence:  0.6,
    });

    faceMesh.onResults((results) => {
      // Preparar canvas
      const ctx = canvasEl.getContext('2d');
      canvasEl.width  = videoEl.videoWidth  || 640;
      canvasEl.height = videoEl.videoHeight || 480;
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

      if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
        actualizarUI(null);
        return;
      }

      const lm  = results.multiFaceLandmarks[0];

      // Calcular EAR de ambos ojos y promediar
      const earIzq = calcEAR(lm, OJO_IZQ);
      const earDer = calcEAR(lm, OJO_DER);
      const ear    = (earIzq + earDer) / 2.0;

      // Detección de parpadeo: flanco de bajada del EAR
      const ojoCerrado = ear < EAR_UMBRAL;
      if (ojoCerrado && !ojoCerradoPrev) {
        // Ojo acaba de cerrarse — cuenta como inicio de parpadeo
      }
      if (!ojoCerrado && ojoCerradoPrev) {
        // Ojo acaba de abrirse — parpadeo completado
        parpadeos++;
      }
      ojoCerradoPrev = ojoCerrado;

      // Contar frames consecutivos con EAR bajo
      if (ojoCerrado) {
        earFramesBajo++;
      } else {
        earFramesBajo = 0;
      }

      // Dibujar contorno de ojos en canvas
      dibujarOjos(ctx, lm, canvasEl.width, canvasEl.height, ojoCerrado);

      // Actualizar UI
      actualizarUI(ear);
      actualizarChart(ear);

      // ── CONDICIÓN DE FATIGA ──
      const ahora          = Date.now();
      const earPersistente = earFramesBajo >= EAR_FRAMES_MIN;
      const parpExcesivo   = parpadeos >= BLINK_UMBRAL;
      const cooldownOk     = (ahora - ultimaAlerta) > COOLDOWN_MS;

      // Log cada 30 frames (~1 seg) para no saturar la consola
      if (earFramesBajo % 30 === 1) {
        console.log(
          `EAR: ${ear.toFixed(3)} | frames bajo: ${earFramesBajo}/${EAR_FRAMES_MIN} | ` +
          `parpadeos: ${parpadeos}/${BLINK_UMBRAL} | cooldown ok: ${cooldownOk} | ` +
          `enviando: ${enviandoFatiga}`
        );
      }

      if (earPersistente && parpExcesivo && cooldownOk && !enviandoFatiga) {
        console.log('🚨 FATIGA DETECTADA — enviando a Django...');
        ultimaAlerta  = ahora;
        earFramesBajo = 0;
        enviarFatiga(ear, parpadeos);
      }
    });

    // Iniciar cámara
    const camera = new Camera(videoEl, {
      onFrame: async () => {
        await faceMesh.send({ image: videoEl });
      },
      width: 640, height: 480,
    });

    camera.start().catch(err => {
      console.error('Error al iniciar cámara:', err);
    });

    // Mantener MediaPipe activo aunque la pestaña esté oculta
    // usando setInterval que no se throttlea como requestAnimationFrame
    let procesandoFrame = false;
    setInterval(async () => {
      // Solo procesar si el video tiene datos y no estamos ya procesando
      if (
        document.visibilityState === 'hidden' &&
        videoEl.readyState === 4 &&
        !procesandoFrame
      ) {
        procesandoFrame = true;
        try {
          await faceMesh.send({ image: videoEl });
        } catch (e) {
          // silencioso
        } finally {
          procesandoFrame = false;
        }
      }
    }, 100); // cada 100ms = ~10fps en segundo plano
  }

  /* ─────────────────────────────────────
     DIBUJAR OJOS EN CANVAS
  ───────────────────────────────────── */
  function dibujarOjos(ctx, lm, w, h, fatigado) {
    // Contornos de los ojos (índices del iris exterior)
    const contornoIzq = [33,160,158,133,153,144];
    const contornoDer = [362,385,387,263,373,380];
    const color       = fatigado ? 'rgba(248,113,113,.9)' : 'rgba(129,140,248,.9)';
    const relleno     = fatigado ? 'rgba(248,113,113,.12)' : 'rgba(129,140,248,.08)';

    [contornoIzq, contornoDer].forEach(grupo => {
      ctx.beginPath();
      grupo.forEach((idx, i) => {
        const x = lm[idx].x * w;
        const y = lm[idx].y * h;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.closePath();
      ctx.strokeStyle = color;
      ctx.lineWidth   = 2;
      ctx.stroke();
      ctx.fillStyle   = relleno;
      ctx.fill();
    });
  }

  /* ─────────────────────────────────────
     ACTUALIZAR UI EN TIEMPO REAL
  ───────────────────────────────────── */
  function actualizarUI(ear) {
    // Actualizar contador de parpadeos en tiempo real (suma actual del minuto)
    if (metricBlink) metricBlink.textContent = parpadeos;

    if (ear === null) {
      if (earDisplay) earDisplay.textContent = '—';
      if (metricEAR)  metricEAR.textContent  = '—';
      if (earBar)     earBar.style.width      = '0%';
      return;
    }

    const earStr = ear.toFixed(3);
    const pct    = Math.min((ear / 0.5) * 100, 100);
    const color  = ear < EAR_UMBRAL ? '#f87171' : '#818cf8';

    if (earDisplay) { earDisplay.textContent = earStr; earDisplay.style.color = color; }
    if (earBar)     { earBar.style.width = pct + '%'; earBar.style.background = color; }
    if (metricEAR)  { metricEAR.textContent = earStr; metricEAR.style.color = color; }
  }

  /* ─────────────────────────────────────
     ENVIAR FATIGA A DJANGO
  ───────────────────────────────────── */
  async function enviarFatiga(ear, parpMin) {
    enviandoFatiga = true;

    const iaLoading = document.getElementById('iaLoading');
    const iaContent = document.getElementById('iaContent');
    if (iaLoading) iaLoading.classList.remove('hidden');
    if (iaContent) iaContent.classList.add('hidden');

    try {
      const resp = await fetch(urlFatiga, {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  csrf,
        },
        body: JSON.stringify({
          ear:                  parseFloat(ear.toFixed(3)),
          parpadeos_por_minuto: parpMin,
          motivo: `EAR ${ear.toFixed(3)} por más de ${Math.round(EAR_FRAMES_MIN/30)} seg + ${parpMin} parpadeos/min`,
        }),
      });

      if (!resp.ok) {
        console.error('Error HTTP:', resp.status);
        return;
      }

      const data = await resp.json();

      if (data.ok) {
        // Actualizar contador de alertas
        if (metricAlertas) {
          metricAlertas.textContent = parseInt(metricAlertas.textContent || '0') + 1;
        }
        // Notificación nativa del SO (funciona aunque esté en otra app)
        EyeGuardNotif.alertaFatiga(data.recomendacion, ear.toFixed(3));
        // Mostrar modal con recomendación
        mostrarModal(data.recomendacion, ear, parpMin);
        // Actualizar panel IA
        actualizarPanelIA(data.recomendacion, ear, data.hora);
        // Agregar al historial en pantalla
        agregarAlHistorial(ear, parpMin, data.hora);
        // Sonido
        playAlertSound();
      } else {
        console.error('Error del servidor:', data.error);
      }
    } catch (err) {
      console.error('Error al enviar fatiga:', err);
    } finally {
      if (iaLoading) iaLoading.classList.add('hidden');
      if (iaContent) iaContent.classList.remove('hidden');
      // Permitir nueva alerta después del cooldown
      setTimeout(() => { enviandoFatiga = false; }, COOLDOWN_MS);
    }
  }

  /* ─────────────────────────────────────
     MODAL DE FATIGA
  ───────────────────────────────────── */
  function mostrarModal(recomendacion, ear, parpMin) {
    const modal      = document.getElementById('alertModal');
    const iaText     = document.getElementById('modalIaText');
    const modalEAR   = document.getElementById('modalEAR');
    const modalBlink = document.getElementById('modalBlink');
    if (!modal) return;
    if (iaText)     iaText.textContent     = recomendacion;
    if (modalEAR)   modalEAR.textContent   = ear.toFixed(3);
    if (modalBlink) modalBlink.textContent = parpMin + '/min';
    modal.classList.remove('hidden');
  }

  window.dismissModal = () => {
    document.getElementById('alertModal')?.classList.add('hidden');
  };

  /* ─────────────────────────────────────
     ACTUALIZAR PANEL IA
  ───────────────────────────────────── */
  function actualizarPanelIA(recomendacion, ear, hora) {
    const iaContent = document.getElementById('iaContent');
    if (!iaContent) return;
    iaContent.innerHTML = `
      <p class="ia-text">${recomendacion}</p>
      <span class="ia-time">${hora} · EAR ${ear.toFixed(3)}</span>
    `;
  }

  /* ─────────────────────────────────────
     AGREGAR ITEM AL HISTORIAL EN PANTALLA
  ───────────────────────────────────── */
  function agregarAlHistorial(ear, parpMin, hora) {
    const list = document.getElementById('histList');
    if (!list) return;
    list.querySelector('.hist-empty-adv')?.remove();

    const div = document.createElement('div');
    div.className = 'hist-item-adv';
    div.innerHTML = `
      <div class="hist-item-left">
        <span class="hist-dot-adv"></span>
        <div>
          <div class="hist-item-name">Fatiga visual detectada</div>
          <div class="hist-item-msg">EAR ${ear.toFixed(3)} · ${parpMin} parp/min</div>
        </div>
      </div>
      <span class="hist-item-time">${hora}</span>
    `;
    list.insertBefore(div, list.firstChild);
  }

  /* ─────────────────────────────────────
     SONIDO
  ───────────────────────────────────── */
  function playAlertSound() {
    try {
      const ctx  = new (window.AudioContext || window.webkitAudioContext)();
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.8);
    } catch (e) {}
  }

});