(function () {
    const root = document.getElementById('report-root');
    const reportId = root.dataset.reportId;

    const STEP_ORDER = ['data_collected', 'news_analysed', 'financials_analysed', 'dcf_complete', 'verdict_predicted', 'report_complete'];

    const statusBadge = document.getElementById('report-status-badge');
    const verdictBadge = document.getElementById('verdict-badge');
    const companyEl = document.getElementById('report-company');
    const errorBanner = document.getElementById('error-banner');
    const generatingNote = document.getElementById('generating-note');
    const downloadBtn = document.getElementById('download-btn');

    const summarySection = document.getElementById('summary-section');
    const summaryText = document.getElementById('summary-text');
    const verdictReasoning = document.getElementById('verdict-reasoning');

    const priceSection = document.getElementById('price-section');
    const priceGrid = document.getElementById('price-grid');

    const newsSection = document.getElementById('news-section');
    const sentimentBadge = document.getElementById('sentiment-badge');
    const sentimentText = document.getElementById('sentiment-text');
    const newsList = document.getElementById('news-list');

    const analysisSection = document.getElementById('analysis-section');
    const bullCaseText = document.getElementById('bull-case-text');
    const bearCaseText = document.getElementById('bear-case-text');
    const strengthsList = document.getElementById('strengths-list');
    const risksList = document.getElementById('risks-list');

    const dcfSection = document.getElementById('dcf-section');
    const dcfIntrinsic = document.getElementById('dcf-intrinsic');
    const dcfCurrentPrice = document.getElementById('dcf-current-price');
    const dcfMargin = document.getElementById('dcf-margin');
    const dcfVerdict = document.getElementById('dcf-verdict');
    const dcfCommentary = document.getElementById('dcf-commentary');
    const dcfAssumptions = document.getElementById('dcf-assumptions');

    const highlightsSection = document.getElementById('highlights-section');
    const highlightsList = document.getElementById('highlights-list');

    const watchSection = document.getElementById('watch-section');
    const watchPills = document.getElementById('watch-pills');

    downloadBtn.addEventListener('click', () => window.print());

    function fmt(value, suffix = '') {
        if (value === null || value === undefined) return '—';
        if (typeof value === 'number') {
            return value.toLocaleString(undefined, { maximumFractionDigits: 2 }) + suffix;
        }
        return value + suffix;
    }

    function metricCard(label, value) {
        const div = document.createElement('div');
        div.className = 'metric-card';
        div.innerHTML = `<span class="metric-label">${label}</span><span class="metric-value">${value}</span>`;
        return div;
    }

    function updateProgress(currentStep) {
        const currentIndex = STEP_ORDER.indexOf(currentStep);
        document.querySelectorAll('.progress-step').forEach((el, i) => {
            el.classList.remove('done', 'active');
            if (i <= currentIndex) el.classList.add('done');
        });
    }

    function renderPrice(priceData, fundamentals) {
        priceGrid.innerHTML = '';
        const rows = [
            ['Sector', priceData.sector],
            ['Current Price', fmt(priceData.current_price, priceData.current_price != null ? ' $' : '')],
            ['Day Change', fmt(priceData.day_change_pct, '%')],
            ['Market Cap', priceData.market_cap ? fmt(priceData.market_cap / 1e9, 'B') : '—'],
            ['P/E Ratio', fmt(fundamentals.pe_ratio)],
            ['EPS', fmt(fundamentals.eps)],
            ['Profit Margin', fundamentals.profit_margin != null ? fmt(fundamentals.profit_margin * 100, '%') : '—'],
            ['ROE', fundamentals.roe != null ? fmt(fundamentals.roe * 100, '%') : '—'],
        ];
        rows.forEach(([label, value]) => priceGrid.appendChild(metricCard(label, value)));
        priceSection.style.display = '';
    }

    function renderNews(newsData) {
        sentimentBadge.textContent = newsData.overall_sentiment || 'Unknown';
        sentimentBadge.className = 'sentiment-badge sentiment-' + (newsData.overall_sentiment || '').toLowerCase().replace(/\s+/g, '-');
        sentimentText.textContent = newsData.sentiment_summary || '';

        newsList.innerHTML = '';
        (newsData.articles || []).slice(0, 5).forEach((article) => {
            const li = document.createElement('li');
            li.className = 'news-item';
            const link = article.url
                ? `<a href="${article.url}" target="_blank" rel="noopener">${article.headline}</a>`
                : article.headline;
            li.innerHTML = `${link} <span class="news-tag news-tag-${(article.sentiment || 'neutral').toLowerCase()}">${article.sentiment || 'Neutral'}</span>`;
            newsList.appendChild(li);
        });
        newsSection.style.display = '';
    }

    function renderAnalysis(analysis) {
        bullCaseText.textContent = analysis.bull_case || '';
        bearCaseText.textContent = analysis.bear_case || '';

        strengthsList.innerHTML = '';
        (analysis.strengths || []).forEach((s) => {
            const li = document.createElement('li');
            li.textContent = s;
            strengthsList.appendChild(li);
        });

        risksList.innerHTML = '';
        (analysis.risks || []).forEach((r) => {
            const li = document.createElement('li');
            li.textContent = r;
            risksList.appendChild(li);
        });

        analysisSection.style.display = '';
    }

    function renderSummary(reportJson) {
        summaryText.textContent = reportJson.executive_summary || '';
        verdictReasoning.textContent = reportJson.verdict_reasoning || '';
        summarySection.style.display = '';

        const verdict = (reportJson.investment_verdict || '').toUpperCase();
        if (verdict) {
            verdictBadge.textContent = verdict;
            verdictBadge.className = 'verdict-badge verdict-' + verdict.toLowerCase();
            verdictBadge.style.display = '';
        }
    }

    function renderDcf(dcf) {
        if (!dcf.available) {
            dcfCommentary.textContent = dcf.reason || dcf.commentary || 'DCF unavailable.';
            dcfSection.style.display = '';
            return;
        }
        dcfIntrinsic.textContent = fmt(dcf.intrinsic_value, ' $');
        dcfCurrentPrice.textContent = fmt(dcf.current_price, ' $');
        dcfMargin.textContent = fmt(dcf.margin_of_safety, '%');
        dcfMargin.style.color = (dcf.margin_of_safety || 0) >= 0 ? 'var(--positive)' : 'var(--negative)';
        dcfVerdict.textContent = dcf.verdict || '—';
        dcfCommentary.textContent = dcf.commentary || '';

        dcfAssumptions.innerHTML = '';
        const assumptions = dcf.assumptions_used || {};
        Object.entries(assumptions).forEach(([key, value]) => {
            const span = document.createElement('span');
            span.className = 'assumption-pill';
            span.textContent = `${key.replace(/_/g, ' ')}: ${value}${key === 'years' ? '' : '%'}`;
            dcfAssumptions.appendChild(span);
        });
        dcfSection.style.display = '';
    }

    function renderHighlights(reportJson) {
        highlightsList.innerHTML = '';
        (reportJson.financial_highlights || []).forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            highlightsList.appendChild(li);
        });
        highlightsSection.style.display = '';
    }

    function renderWatchMetrics(reportJson) {
        watchPills.innerHTML = '';
        (reportJson.key_metrics_to_watch || []).forEach((item) => {
            const span = document.createElement('span');
            span.className = 'pill';
            span.textContent = item;
            watchPills.appendChild(span);
        });
        watchSection.style.display = '';
    }

    let polling = true;

    async function poll() {
        if (!polling) return;
        try {
            const res = await fetch('/api/report/' + reportId);
            const report = await res.json();

            statusBadge.textContent = report.status;
            statusBadge.className = 'status-badge status-' + report.status;
            if (report.company_name) companyEl.textContent = report.company_name;

            updateProgress(report.current_step);

            if (report.price_data && report.fundamentals) {
                renderPrice(report.price_data, report.fundamentals);
            }
            if (report.news_json) {
                renderNews(report.news_json);
            }
            if (report.analysis_json) {
                renderAnalysis(report.analysis_json);
            }
            if (report.dcf_json) {
                renderDcf(report.dcf_json);
            }
            if (report.report_json) {
                renderSummary(report.report_json);
                renderHighlights(report.report_json);
                renderWatchMetrics(report.report_json);
            }

            if (report.status === 'error') {
                errorBanner.textContent = report.error_message || 'Something went wrong generating this report.';
                errorBanner.style.display = '';
                generatingNote.style.display = 'none';
                polling = false;
                return;
            }

            if (report.status === 'done') {
                generatingNote.style.display = 'none';
                downloadBtn.style.display = '';
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
