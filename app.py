import os
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# --- LOGIQUE DE CALCUL DOUANIER EN PYTHON (BACKEND) ---
def liquidation_logic(caf, config):
    dd = caf * config['taux_dd']
    rs = caf * 0.01
    pcs = caf * 0.008
    pc_cdao = caf * 0.005
    cosec = caf * 0.004

    da = (caf + dd + rs) * config['taux_assise'] if config['taux_assise'] > 0 else 0.0
    promad = caf * 0.02 if config['promad'] else 0.0

    assiette_tva_bic = caf + dd + rs + da
    tva = assiette_tva_bic * 0.18
    bic = assiette_tva_bic * 0.03

    mdt = dd + rs + pcs + pc_cdao + da + cosec + promad + tva + bic

    return {
        "elements": [
            {"label": "Valeur en Douane (CAF)", "val": round(caf, 2)},
            {"label": "Droit de Douane (DD)", "val": round(dd, 2)},
            {"label": "Redevance Statistique (RS)", "val": round(rs, 2)},
            {"label": "PCS (Solidarité)", "val": round(pcs, 2)},
            {"label": "Prélèvement CDAO", "val": round(pc_cdao, 2)},
            {"label": "Droit d'Assise", "val": round(da, 2)},
            {"label": "COSEC", "val": round(cosec, 2)},
            {"label": "PROMAD", "val": round(promad, 2)},
            {"label": "TVA (18%)", "val": round(tva, 2)},
            {"label": "BIC (3%)", "val": round(bic, 2)}
        ],
        "total": round(mdt, 0)
    }


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    choix = int(data.get('choix', 1))
    fret_global = float(data.get('fret', 0))
    ass_locale = float(data.get('ass_locale', 0))
    mode_ass = data.get('mode_assurance')

    total_fob = float(data.get('fob_total', 0))
    cfr_global = total_fob + fret_global

    # Étape 3 : Calcul de l'assurance globale
    ass_total = 0.0
    if mode_ass == "1":
        ass_maritime = float(data.get('ass_maritime', 0))
        ass_total = ass_maritime + ((ass_locale + 1000) * 1.05)
    else:
        p_simple = float(data.get('p_simple', 0))
        p_maj = float(data.get('p_maj', 0))
        ass_retenue = (1 + (p_maj / 100)) * (p_simple / 100)

        if mode_ass == "2":
            ass_total = (cfr_global * ass_retenue) + ((ass_locale + 1000) * 1.05)
        elif mode_ass == "3":
            cif_exact = cfr_global / (1 - ass_retenue) if (1 - ass_retenue) > 0 else cfr_global
            ass_total = (cif_exact - cfr_global) + ((ass_locale + 1000) * 1.05)

    results = []

    # Étape 4 & 5 : Répartition et Liquidation
    if choix == 1:
        caf = total_fob + fret_global + ass_total
        res = liquidation_logic(caf, data['configs'][0])
        results.append(res)
    else:
        poids_total = float(data.get('poids_total', 1))
        if poids_total <= 0: poids_total = 1.0

        for i in range(2):
            fob_art = float(data['articles'][i]['fob'])
            poids_art = float(data['articles'][i]['poids'])

            ass_art = ass_total * (fob_art / total_fob) if total_fob > 0 else 0.0
            fret_art = fret_global * (poids_art / poids_total)
            caf_art = fob_art + ass_art + fret_art

            results.append(liquidation_logic(caf_art, data['configs'][i]))

    return jsonify({"results": results, "global_total": sum(r['total'] for r in results)})


# --- INTERFACE DE RENDU (FRONTEND INTEGRÉ EN HTML/CSS/JS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DouanePro | Calculateur de Liquidation</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
        .card { background: white; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); border: 1px solid #e2e8f0; }
    </style>
</head>
<body class="p-4 md:p-8">

    <div class="max-w-6xl mx-auto">
        <header class="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 pb-6 border-b border-slate-200 gap-4">
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">🛃 DouanePro</h1>
                <p class="text-slate-500 mt-1">Interface de liquidation douanière automatisée (Normes UEMOA - Flask Server)</p>
            </div>
            <span class="bg-blue-50 text-blue-700 px-4 py-1.5 rounded-full text-sm font-semibold border border-blue-100">Python Backend Ready</span>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">

            <div class="lg:col-span-2 space-y-6">

                <div class="card p-6">
                    <h2 class="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">⏱️ Étape 1 : Nombre d'articles</h2>
                    <div class="flex gap-4">
                        <button onclick="setChoix(1)" id="btn-1" class="flex-1 py-3 rounded-xl border-2 font-bold transition-all">1 Article Unique</button>
                        <button onclick="setChoix(2)" id="btn-2" class="flex-1 py-3 rounded-xl border-2 font-bold transition-all">2 Articles Distincts</button>
                    </div>
                </div>

                <div class="card p-6" id="articles-container"></div>

                <div class="card p-6">
                    <h2 class="text-lg font-bold text-slate-800 mb-4">🛡️ Étape 3 : Fret & Assurance Transport</h2>

                    <div class="space-y-4">
                        <div>
                            <label class="block text-sm font-semibold text-slate-700 mb-1">Mode de calcul de l'assurance</label>
                            <select id="mode_ass" onchange="toggleAssuranceFields()" class="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none">
                                <option value="1">1. J'ai la valeur de l'assurance (Maritime / Locale)</option>
                                <option value="2">2. Calculer avec CFR + Majoration %</option>
                                <option value="3">3. Calculer avec le CIF</option>
                            </select>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-slate-600">Valeur du Fret Global (F CFA)</label>
                                <input type="number" id="fret" value="0" class="w-full mt-1 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-slate-600">Assurance Locale (F CFA)</label>
                                <input type="number" id="ass_locale" value="0" class="w-full mt-1 border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none">
                            </div>
                        </div>

                        <div id="dynamic-ass-fields" class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2"></div>
                    </div>
                </div>

                <button onclick="calculateLiquidation()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg transition-all transform active:scale-[0.99] flex items-center justify-center gap-2 text-lg">
                    🔥 CALCULER LA LIQUIDATION DOUANIÈRE
                </button>
            </div>

            <div class="lg:col-span-1">
                <div class="card p-6 sticky top-8 border-t-4 border-blue-600 bg-slate-50/50">
                    <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">🧾 Rapport de Calcul</h2>

                    <div id="results-display" class="space-y-6">
                        <div class="text-center py-12 text-slate-400">
                            <p class="text-4xl mb-2">📊</p>
                            <p class="text-sm">Renseignez les champs et cliquez sur Calculer pour générer le bilan.</p>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        let choixActuel = 1;

        function setChoix(n) {
            choixActuel = n;
            document.getElementById('btn-1').className = n === 1 ? 'flex-1 py-3 rounded-xl border-2 border-blue-600 bg-blue-50 text-blue-700 font-bold' : 'flex-1 py-3 rounded-xl border-2 border-slate-200 text-slate-500 bg-white hover:bg-slate-50 font-medium';
            document.getElementById('btn-2').className = n === 2 ? 'flex-1 py-3 rounded-xl border-2 border-blue-600 bg-blue-50 text-blue-700 font-bold' : 'flex-1 py-3 rounded-xl border-2 border-slate-200 text-slate-500 bg-white hover:bg-slate-50 font-medium';
            renderArticlesForm();
        }

        function renderArticlesForm() {
            const container = document.getElementById('articles-container');
            let html = '<h2 class="text-lg font-bold text-slate-800 mb-4">📦 Étape 2 : Saisie des Articles & Configuration Fiscale</h2>';

            for (let i = 1; i <= choixActuel; i++) {
                html += `
                <div class="mb-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <h3 class="font-bold text-blue-700 mb-3 flex items-center gap-2">📦 ${choixActuel === 1 ? 'Article Unique' : 'Article ' + i}</h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                            <label class="block text-xs font-semibold uppercase text-slate-500">FOB Unitaire</label>
                            <input type="number" id="fob_u_${i}" value="0" class="w-full mt-1 border border-slate-300 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold uppercase text-slate-500">Nombre de Colis</label>
                            <input type="number" id="qty_${i}" value="0" class="w-full mt-1 border border-slate-300 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold uppercase text-slate-500">Poids Brut (kg)</label>
                            <input type="number" id="poids_${i}" value="0" step="0.1" class="w-full mt-1 border border-slate-300 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-blue-500" ${choixActuel === 1 ? 'disabled placeholder="Non requis"' : ''}>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-3 border-t border-slate-200/60">
                        <div>
                            <label class="block text-xs font-semibold uppercase text-slate-500">Catégorie de Droits de Douane</label>
                            <select id="cat_${i}" class="w-full mt-1 border border-slate-300 rounded-lg p-2 bg-white outline-none focus:ring-2 focus:ring-blue-500">
                                <option value="0">Catégorie 0 (0%)</option>
                                <option value="0.05">Catégorie 1 (5%)</option>
                                <option value="0.10">Catégorie 2 (10%)</option>
                                <option value="0.20">Catégorie 3 (20%)</option>
                                <option value="0.35">Catégorie 4 (35%)</option>
                            </select>
                        </div>
                        <div class="flex flex-col justify-end space-y-2 pb-1">
                            <label class="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                                <input type="checkbox" id="assise_check_${i}" onchange="toggleAssiseInput(${i})" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500">
                                Ajouter le Droit d'Assise ?
                            </label>
                            <div id="assise_val_container_${i}" class="hidden">
                                <input type="number" id="assise_taux_${i}" value="5" class="w-24 border border-slate-300 rounded-lg p-1 text-sm inline-block outline-none focus:ring-2 focus:ring-blue-500"> % taux d'assise
                            </div>
                            <label class="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                                <input type="checkbox" id="promad_${i}" class="rounded border-slate-300 text-blue-600 focus:ring-blue-500">
                                Ajouter la taxe PROMAD (2%) ?
                            </label>
                        </div>
                    </div>
                </div>`;
            }
            container.innerHTML = html;
        }

        function toggleAssiseInput(i) {
            const container = document.getElementById(`assise_val_container_${i}`);
            const checkbox = document.getElementById(`assise_check_${i}`);
            if (checkbox.checked) container.classList.remove('hidden');
            else container.classList.add('hidden');
        }

        function toggleAssuranceFields() {
            const mode = document.getElementById('mode_ass').value;
            const target = document.getElementById('dynamic-ass-fields');

            if (mode === "1") {
                target.innerHTML = `
                    <div class="col-span-2">
                        <label class="block text-sm font-medium text-slate-600">Assurance Maritime / Directe (F CFA)</label>
                        <input type="number" id="ass_maritime" value="0" class="w-full mt-1 border border-slate-300 rounded-lg p-2.5">
                    </div>`;
            } else {
                target.innerHTML = `
                    <div>
                        <label class="block text-sm font-medium text-slate-600">Pourcentage simple (%)</label>
                        <input type="number" id="p_simple" value="4" step="0.01" class="w-full mt-1 border border-slate-300 rounded-lg p-2.5">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-slate-600">Pourcentage majoré (%)</label>
                        <input type="number" id="p_maj" value="10" step="0.01" class="w-full mt-1 border border-slate-300 rounded-lg p-2.5">
                    </div>`;
            }
        }

        async function calculateLiquidation() {
            const data = {
                choix: choixActuel,
                fret: parseFloat(document.getElementById('fret').value) || 0,
                mode_assurance: document.getElementById('mode_ass').value,
                ass_locale: parseFloat(document.getElementById('ass_locale').value) || 0,
                ass_maritime: parseFloat(document.getElementById('ass_maritime')?.value) || 0,
                p_simple: parseFloat(document.getElementById('p_simple')?.value) || 0,
                p_maj: parseFloat(document.getElementById('p_maj')?.value) || 0,
                configs: [],
                articles: []
            };

            let totalFob = 0;
            let totalPoids = 0;

            for (let i = 1; i <= choixActuel; i++) {
                let unitaire = parseFloat(document.getElementById(`fob_u_${i}`).value) || 0;
                let qte = parseFloat(document.getElementById(`qty_${i}`).value) || 0;
                let fob_art = unitaire * qte;
                let poids_art = parseFloat(document.getElementById(`poids_${i}`).value) || 0;

                totalFob += fob_art;
                totalPoids += poids_art;

                let hasAssise = document.getElementById(`assise_check_${i}`).checked;
                let tauxAssise = hasAssise ? (parseFloat(document.getElementById(`assise_taux_${i}`).value) / 100) : 0;
                let hasPromad = document.getElementById(`promad_${i}`).checked;

                data.articles.push({ fob: fob_art, poids: poids_art });
                data.configs.push({
                    taux_dd: parseFloat(document.getElementById(`cat_${i}`).value),
                    taux_assise: tauxAssise,
                    promad: hasPromad
                });
            }

            data.fob_total = totalFob;
            data.poids_total = totalPoids;

            if (totalFob <= 0) {
                alert("⚠️ Erreur : Veuillez renseigner des valeurs FOB supérieures à 0.");
                return;
            }

            // Communication asynchrone avec le serveur Python (Flask API)
            const response = await fetch('/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            displayResults(result);
        }

        function displayResults(data) {
            const display = document.getElementById('results-display');

            let html = `
                <div class="bg-blue-600 text-white text-center p-4 rounded-xl shadow-inner">
                    <span class="text-xs uppercase tracking-wider opacity-80">Montant Global Combiné à Payer</span>
                    <div class="text-3xl font-black mt-1">${data.global_total.toLocaleString('fr-FR')} F CFA</div>
                </div>
                <div class="space-y-4">
            `;

            data.results.forEach((res, index) => {
                html += `
                    <div class="bg-white p-4 rounded-xl border border-slate-200">
                        <div class="flex justify-between items-center mb-3 pb-2 border-b border-slate-100">
                            <h4 class="font-bold text-slate-800">${choixActuel === 1 ? 'Bilan de la Liquidation' : 'Article ' + (index + 1)}</h4>
                            <span class="text-blue-600 font-bold text-sm">${res.total.toLocaleString('fr-FR')} F CFA</span>
                        </div>
                        <div class="space-y-1.5 text-xs">
                `;

                res.elements.forEach(el => {
                    const isCAF = el.label.includes('CAF');
                    html += `
                        <div class="flex justify-between ${isCAF ? 'font-semibold text-slate-900 pt-1 border-t border-dashed border-slate-200' : 'text-slate-500'}">
                            <span>${el.label}</span>
                            <span>${Math.round(el.val).toLocaleString('fr-FR')}</span>
                        </div>
                    `;
                });

                html += `</div></div>`;
            });

            html += `</div>`;
            display.innerHTML = html;
        }

        setChoix(1);
        toggleAssuranceFields();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)