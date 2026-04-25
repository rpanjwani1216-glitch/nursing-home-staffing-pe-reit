clear all
set more off

global project_root "/Users/rohanpanjwani/School/ECON_1430/Final_Project"
global table_dir "${project_root}/outputs/intermediate/tables/econometrics"
global fig_dir "${project_root}/outputs/intermediate/figures/econometrics"

cap mkdir "${fig_dir}"

* Current csdid event-study figures with correct names
foreach spec in total_nurse rn {
    use "${table_dir}/csdid_event_`spec'_plot_data.dta", clear
    gen x = .
    replace x = 1 if term == "Tm2"
    replace x = 2 if term == "Tm1"
    replace x = 3 if term == "Tp0"
    replace x = 4 if term == "Tp1"
    replace x = 5 if term == "Tp2"
    keep if inlist(term, "Tm2", "Tm1", "Tp0", "Tp1", "Tp2")

    foreach panel in "National" "Same-state" "Matched" {
        preserve
            keep if panel == `"`panel'"'
            local suffix = cond("`panel'" == "National", "gold_v2", cond("`panel'" == "Same-state", "gold_v2_same_state", "gold_v2_same_state_matched"))
            local title_outcome = cond("`spec'" == "total_nurse", "Total nurse HPRD", "RN HPRD")
            twoway ///
                (rcap lb ub x, lcolor(navy)) ///
                (connected coef x, lcolor(navy) mcolor(navy) msymbol(D)), ///
                xlabel(1 "t-2" 2 "t-1" 3 "t" 4 "t+1" 5 "t+2") ///
                yline(0, lpattern(dash) lcolor(black)) ///
                xtitle("Event time") ///
                ytitle("Coefficient (95% CI)") ///
                title("`title_outcome': `panel'") ///
                legend(off) ///
                graphregion(color(white))
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.png", replace width(1800)
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.pdf", replace
        restore
    }
}

* Current csdid event-study figures for star ratings
foreach spec in health_rating overall_rating staffing_rating qm_rating {
    use "${table_dir}/csdid_event_`spec'_plot_data.dta", clear
    gen x = .
    replace x = 1 if term == "Tm2"
    replace x = 2 if term == "Tm1"
    replace x = 3 if term == "Tp0"
    replace x = 4 if term == "Tp1"
    replace x = 5 if term == "Tp2"
    keep if inlist(term, "Tm2", "Tm1", "Tp0", "Tp1", "Tp2")

    local title_outcome = cond("`spec'" == "health_rating", "Health rating", ///
        cond("`spec'" == "overall_rating", "Overall rating", ///
        cond("`spec'" == "staffing_rating", "Staffing rating", "QM rating")))

    foreach panel in "National" "Same-state" "Matched" {
        preserve
            keep if panel == `"`panel'"'
            local suffix = cond("`panel'" == "National", "gold_v2", cond("`panel'" == "Same-state", "gold_v2_same_state", "gold_v2_same_state_matched"))
            twoway ///
                (rcap lb ub x, lcolor(navy)) ///
                (connected coef x, lcolor(navy) mcolor(navy) msymbol(D)), ///
                xlabel(1 "t-2" 2 "t-1" 3 "t" 4 "t+1" 5 "t+2") ///
                yline(0, lpattern(dash) lcolor(black)) ///
                xtitle("Event time") ///
                ytitle("Coefficient (95% CI)") ///
                title("`title_outcome': `panel'") ///
                legend(off) ///
                graphregion(color(white))
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.png", replace width(1800)
            graph export "${fig_dir}/csdid_event_`spec'_`suffix'.pdf", replace
        restore
    }
}

* Part A: main staffing coefficient plot
use "${table_dir}/paper_main_coef_plot_data.dta", clear
gen y = .
replace y = 3 if panel == "National"
replace y = 2 if panel == "Same-state"
replace y = 1 if panel == "Matched"

preserve
    keep if outcome == "Total nurse HPRD"
    twoway ///
        (rcap lb ub y, horizontal lcolor(navy)) ///
        (scatter y coef, msymbol(D) mcolor(navy) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Estimated post-takeover effect (95% CI)") ///
        title("Total nurse HPRD") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_main_total, replace)
restore

preserve
    keep if outcome == "RN HPRD"
    twoway ///
        (rcap lb ub y, horizontal lcolor(maroon)) ///
        (scatter y coef, msymbol(D) mcolor(maroon) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Estimated post-takeover effect (95% CI)") ///
        title("RN HPRD") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_main_rn, replace)
restore

graph combine g_main_total g_main_rn, ///
    cols(1) ///
    title("Main staffing effects across control designs") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_main_staffing_coefficients.png", replace width(1800)
graph export "${fig_dir}/paper_main_staffing_coefficients.pdf", replace


* Secondary outcomes: star rating coefficient plot
use "${table_dir}/paper_star_main_coef_plot_data.dta", clear
gen y = .
replace y = 3 if panel == "National"
replace y = 2 if panel == "Same-state"
replace y = 1 if panel == "Matched"

foreach outcome in "Health rating" "Overall rating" "Staffing rating" "QM rating" {
    preserve
        keep if outcome == `"`outcome'"'
        local gname = cond("`outcome'" == "Health rating", "g_star_health", ///
            cond("`outcome'" == "Overall rating", "g_star_overall", ///
            cond("`outcome'" == "Staffing rating", "g_star_staffing", "g_star_qm")))
        twoway ///
            (rcap lb ub y, horizontal lcolor(navy)) ///
            (scatter y coef, msymbol(D) mcolor(navy) msize(medlarge)), ///
            ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
            yscale(range(0.5 3.5)) ///
            xline(0, lpattern(dash) lcolor(black)) ///
            xtitle("Estimated post-takeover effect (95% CI)") ///
            title("`outcome'") ///
            legend(off) ///
            graphregion(color(white)) ///
            name(`gname', replace)
    restore
}

graph combine g_star_health g_star_overall g_star_staffing g_star_qm, ///
    cols(2) ///
    title("Main star-rating effects across control designs") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_star_ratings_coefficients.png", replace width(2200)
graph export "${fig_dir}/paper_star_ratings_coefficients.pdf", replace


* Part B: Medicaid pretrend diagnostic figure
use "${table_dir}/paper_medicaid_pretrend_plot_data.dta", clear
gen x = term_order + 1
gen x_plot = x
replace x_plot = x - 0.08 if group == "High Medicaid"
replace x_plot = x + 0.08 if group == "Low Medicaid"

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        twoway ///
            (rcap lb ub x_plot if group == "High Medicaid", lcolor(maroon)) ///
            (connected coef x_plot if group == "High Medicaid", mcolor(maroon) lcolor(maroon) msymbol(circle)) ///
            (rcap lb ub x_plot if group == "Low Medicaid", lcolor(navy)) ///
            (connected coef x_plot if group == "Low Medicaid", mcolor(navy) lcolor(navy) msymbol(diamond)), ///
            xlabel(1 "Tm2" 2 "Tm1" 3 "Pre avg") ///
            xscale(range(0.7 3.3)) ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("") ///
            ytitle("Coefficient (95% CI)") ///
            title(`"`panel'"') ///
            legend(order(2 "High Medicaid" 4 "Low Medicaid") rows(1) pos(6)) ///
            graphregion(color(white)) ///
            name(g_med_`=strtoname("`panel'")', replace)
    restore
}

graph combine g_med_National g_med_Same_state g_med_Matched, ///
    cols(3) ///
    title("Pre-treatment coefficients by Medicaid group") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_medicaid_pretrend_diagnostics.png", replace width(2200)
graph export "${fig_dir}/paper_medicaid_pretrend_diagnostics.pdf", replace


* Part B: descriptive Medicaid-share versus staffing-change figure
use "${table_dir}/paper_baseline_medicaid_vs_staffing_change_data.dta", clear
gen short_label = ""
replace short_label = label if label_flag == 1

twoway ///
    (lfit post_minus_pre baseline_medicaid_share, lcolor(maroon) lwidth(medthick)) ///
    (scatter post_minus_pre baseline_medicaid_share, ///
        mcolor(navy%75) msymbol(circle) msize(medlarge) ///
        mlabel(short_label) mlabsize(vsmall) mlabposition(0) mlabcolor(gs6)), ///
    yline(0, lpattern(dash) lcolor(black)) ///
    xtitle("Baseline Medicaid share") ///
    ytitle("Post minus pre total nurse HPRD") ///
    title("Treated facilities: Medicaid dependence and staffing change") ///
    legend(order(1 "Linear fit" 2 "Facility") rows(1) pos(6)) ///
    graphregion(color(white))
graph export "${fig_dir}/paper_baseline_medicaid_vs_staffing_change.png", replace width(1800)
graph export "${fig_dir}/paper_baseline_medicaid_vs_staffing_change.pdf", replace


* Part C: holdco event-study style figure
use "${table_dir}/paper_holdco_event_plot_data.dta", clear
gen x = event_order + 1
gen x_plot = x
replace x_plot = x - 0.08 if group == "HoldCo"
replace x_plot = x + 0.08 if group == "No HoldCo"

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        twoway ///
            (rcap lb ub x_plot if group == "HoldCo", lcolor(maroon)) ///
            (connected coef x_plot if group == "HoldCo", mcolor(maroon) lcolor(maroon) msymbol(circle)) ///
            (rcap lb ub x_plot if group == "No HoldCo", lcolor(navy)) ///
            (connected coef x_plot if group == "No HoldCo", mcolor(navy) lcolor(navy) msymbol(diamond)), ///
            xlabel(1 "t-2" 2 "t-1" 3 "t" 4 "t+1" 5 "t+2") ///
            xscale(range(0.7 5.3)) ///
            yline(0, lpattern(dash) lcolor(black)) ///
            xtitle("Event time") ///
            ytitle("Coefficient (95% CI)") ///
            title(`"`panel'"') ///
            legend(order(2 "HoldCo" 4 "No HoldCo") rows(1) pos(6)) ///
            graphregion(color(white)) ///
            name(g_holdco_evt_`=strtoname("`panel'")', replace)
    restore
}

graph combine g_holdco_evt_National g_holdco_evt_Same_state g_holdco_evt_Matched, ///
    cols(3) ///
    title("Total nurse event-study by HoldCo exposure") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_holdco_event_study.png", replace width(2200)
graph export "${fig_dir}/paper_holdco_event_study.pdf", replace


* Part C: holdco mechanism coefficient plot
use "${table_dir}/paper_holdco_coef_plot_data.dta", clear
gen y = .
replace y = 3 if column == "National"
replace y = 2 if column == "Same-state"
replace y = 1 if column == "Matched"

preserve
    keep if term_label == "HoldCo transition"
    twoway ///
        (rcap lb ub y, horizontal lcolor(navy)) ///
        (scatter y coef, msymbol(D) mcolor(navy) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Coefficient (95% CI)") ///
        title("HoldCo transition") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_hc_base, replace)
restore

preserve
    keep if term_label == "High Medicaid × HoldCo"
    twoway ///
        (rcap lb ub y, horizontal lcolor(maroon)) ///
        (scatter y coef, msymbol(D) mcolor(maroon) msize(medlarge)), ///
        ylabel(1 "Matched" 2 "Same-state" 3 "National", angle(0)) ///
        yscale(range(0.5 3.5)) ///
        xline(0, lpattern(dash) lcolor(black)) ///
        xtitle("Coefficient (95% CI)") ///
        title("High Medicaid × HoldCo") ///
        legend(off) ///
        graphregion(color(white)) ///
        name(g_hc_int, replace)
restore

graph combine g_hc_base g_hc_int, ///
    cols(1) ///
    title("Holding-company mechanism estimates") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_holdco_mechanism_coefficients.png", replace width(1800)
graph export "${fig_dir}/paper_holdco_mechanism_coefficients.pdf", replace


* Part C: 2x2 slack support graphic
use "${table_dir}/paper_slack_support_plot_data.dta", clear
gen x = high_medicare + 1
gen y = high_medicaid + 1
gen cell_code = ""
replace cell_code = "LS" if slack_label == "Least slack"
replace cell_code = "L/L" if slack_label == "Low/Low"
replace cell_code = "H/H" if slack_label == "High/High"
replace cell_code = "MS" if slack_label == "Most slack"
gen display_label = cell_code + "  T:" + string(treated_facility, "%9.0f") + "  A:" + string(facility_count, "%9.0f")

foreach panel in "National" "Same-state" "Matched" {
    preserve
        keep if panel == `"`panel'"'
        twoway ///
            (scatter y x, ///
                msymbol(square) msize(huge) mcolor(gs13) ///
                mlabel(display_label) mlabsize(vsmall) mlabposition(0) mlabcolor(black)), ///
            xlabel(1 "Low Mcare" 2 "High Mcare", labsize(small)) ///
            ylabel(1 "Low Mdcd" 2 "High Mdcd", angle(0) labsize(small)) ///
            xscale(range(0.6 2.4)) ///
            yscale(range(0.6 2.4)) ///
            xtitle("") ytitle("") ///
            title(`"`panel'"') ///
            legend(off) ///
            graphregion(color(white)) ///
            name(g_slack_`=strtoname("`panel'")', replace)
    restore
}

graph combine g_slack_National g_slack_Same_state g_slack_Matched, ///
    cols(3) ///
    title("2x2 slack cells: treated support and total facility counts") ///
    graphregion(color(white))
graph export "${fig_dir}/paper_slack_support_heatmap.png", replace width(2400)
graph export "${fig_dir}/paper_slack_support_heatmap.pdf", replace
