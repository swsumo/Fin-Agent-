(function () {
    const root = document.getElementById('analysis-root');
    const analysisId = root.dataset.analysisId;

    const STEP_ORDER = ['extracting', 'researching', 'synthesizing', 'complete'];

    const statusBadge = document.getElementById('analysis-status-badge');
    const errorBanner = document.getElementById('error-banner');
    const generatingNote = document.getElementById('generating-note');

    const summarySection = document.getElementById('summary-section');
    const portfolioSummaryText = document.getElementById('portfolio-summary-text');
    const marketContextText = document.getElementById('market-context-text');

    const holdingsSection = document.getElementById('holdings-section');
    const holdingsBody = document.getElementById('holdings-body');
    const holdingsReasoning = document.getElementById('holdings-reasoning');

    const historicalSection = document.getElementById('historical-section');
    const historicalText = document.getElementById('historical-text');

    const overallSection = document.getElementById('overall-section');
    const overallText = document.getElementById('overall-text');

    const CURRENCY_SYMBOLS = { USD: '$', INR: '₹', GBP: '£', EUR: '€', JPY: '¥' };

    function fmt(value, prefix = '', suffix = '') {
        if (value === null || value === undefined) return '—';
        if (typeof value === 'number') {
            return prefix + value.toLocaleString(undefined, { maximumFractionDigits: 2 }) + suffix;
        }
        return prefix + value + suffix;
    }

    function fmtMoney(value, currency) {
        if (value === null || value === undefined) return '—';
        const symbol = CURRENCY_SYMBOLS[currency] || (currency ? currency + ' ' : '$');
        return fmt(value, symbol);
    }

    function updateProgress(currentStep) {
        const currentIndex = STEP_ORDER.indexOf(currentStep);
        document.querySelectorAll('.progress-step').forEach((el, i) => {
            el.classList.remove('done');
            if (i <= currentIndex) el.classList.add('done');
        });
    }

    function renderHoldings(enrichment, analysis) {
        const recommendations = {};
        (analysis && analysis.holdings || []).forEach((h) => { recommendations[h.ticker] = h; });

        holdingsBody.innerHTML = '';
        holdingsReasoning.innerHTML = '';

        enrichment.forEach((h) => {
            const rec = recommendations[h.ticker];
            const tr = document.createElement('tr');
            const plClass = (h.unrealized_pl_pct || 0) >= 0 ? 'positive-text' : 'negative-text';
            tr.innerHTML = `
                <td>${h.ticker}</td>
                <td>${fmtMoney(h.avg_price, h.currency)}</td>
                <td>${fmt(h.shares)}</td>
                <td>${h.error ? '—' : fmtMoney(h.current_price, h.currency)}</td>
                <td class="${plClass}">${h.error ? h.error : fmt(h.unrealized_pl_pct, '', '%')}</td>
                <td><span class="verdict-badge verdict-${(rec ? rec.recommendation : 'hold').toLowerCase().replace(/\\s+/g, '-')}">${rec ? rec.recommendation : '—'}</span></td>
            `;
            holdingsBody.appendChild(tr);

            if (rec && rec.reasoning) {
                const p = document.createElement('p');
                p.className = 'holding-reasoning';
                p.innerHTML = `<strong>${h.ticker}:</strong> ${rec.reasoning}`;
                holdingsReasoning.appendChild(p);
            }
        });

        holdingsSection.style.display = '';
    }

    let polling = true;

    async function poll() {
        if (!polling) return;
        try {
            const res = await fetch('/api/analysis/' + analysisId);
            const analysis = await res.json();

            statusBadge.textContent = analysis.status;
            statusBadge.className = 'status-badge status-' + analysis.status;
            updateProgress(analysis.current_step);

            if (analysis.enrichment_json) {
                renderHoldings(analysis.enrichment_json, analysis.analysis_json);
            }

            if (analysis.analysis_json) {
                portfolioSummaryText.textContent = analysis.analysis_json.portfolio_summary || '';
                marketContextText.textContent = analysis.analysis_json.overall_market_context || '';
                summarySection.style.display = '';

                historicalText.textContent = analysis.analysis_json.historical_parallel || '';
                historicalSection.style.display = '';

                overallText.textContent = analysis.analysis_json.overall_recommendation || '';
                overallSection.style.display = '';
            }

            if (analysis.status === 'error') {
                errorBanner.textContent = analysis.error_message || 'Something went wrong analyzing your portfolio.';
                errorBanner.style.display = '';
                generatingNote.style.display = 'none';
                polling = false;
                return;
            }

            if (analysis.status === 'done') {
                generatingNote.style.display = 'none';
                polling = false;
                return;
            }
        } catch (err) {
            // Network hiccup — keep polling.
        }
        setTimeout(poll, 2000);
    }

    poll();
})();
