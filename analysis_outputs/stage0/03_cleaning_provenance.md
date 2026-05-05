# Stage 0 — Cleaning Provenance

Every transformation applied to the raw file `echo_project_update.xlsx` in producing `01_clean_flat.csv`. Each step references the decision-log entry that authorized it.

| # | Decision | Action | Detail |
|---|---|---|---|
| 1 | DEC-011 | whitespace_strip | HD/PD: removed 1 whitespace-variant levels: ['HD '] |
| 2 | DEC-011 | whitespace_strip | m/f: removed 1 whitespace-variant levels: ['m '] |
| 3 | DEC-011 | whitespace_strip | LeftVentricleSystolicFunction: removed 1 whitespace-variant levels: ['Preserved '] |
| 4 | DEC-011 | whitespace_strip | LeftVentricleSummary: removed 17 whitespace-variant levels: ['  ', 'Apical Hypertrophy   Hypertrophy of basal interventricular septum   ', 'C/W LV diastolic dysfunction: Pseudo-normal filling pattern .  ', 'C/W LV diastolic dysfunction: Pseudo-normal filling pattern .   ', 'C/W LV diastolic dysfunction: Restricitive filling pattern .   '] |
| 5 | DEC-011 | whitespace_strip | AorticValveStructure: removed 2 whitespace-variant levels: ['Prosthetic ', 'Thickened '] |
| 6 | DEC-011 | whitespace_strip | AorticValveSummary: removed 10 whitespace-variant levels: ['  ', 'Mild aortic stenosis  ', 'Mild aortic stenosis   ', 'Mild-moderate aortic stenosis   ', 'Minimal aortic stenosis   '] |
| 7 | DEC-011 | whitespace_strip | MitralValveStructure: removed 1 whitespace-variant levels: ['Rheumatic '] |
| 8 | DEC-011 | whitespace_strip | MitralRegurgitation: removed 1 whitespace-variant levels: ['Mild '] |
| 9 | DEC-011 | whitespace_strip | MitralValveSummary: removed 19 whitespace-variant levels: [' Severe mitral stenosis.  Severe mitral annular calcification.', 'Caseous mitral annulus abscess   Mitral annular calcification.   ', 'Mild annular calcification.  ', 'Mild mitral annular calcification.  ', 'Mild mitral annular calcification.   '] |
| 10 | DEC-011 | whitespace_strip | TricuspidValveStructure: removed 2 whitespace-variant levels: ['Normal ', 'Thickened '] |
| 11 | DEC-011 | whitespace_strip | ProcedureSummary: removed 127 whitespace-variant levels: ['  חדר שמאלי ברוחב תקין, דפנותיו בעובי תקין, תפקודו הגלובלי  תקין. חדר ימין ברוחב ותפקוד תקין. פרוזדורים ברוחב תקין. אנולוס מיטרלי מסוייד, דלף מיטרלי מינימלי, דלף טריקוספידלי קל עד בינוני, לחץ ריאתי מוגבר במידה קלה. לא הודגם תפליט פריקרדיאלי', " חדר שמאל בגודל תקין, היפרטרופי, התכווצותו הגךלובלית והאזורית תקינה, חדר ימין תקין, מסתם אאורטלי מעט מסוייד, טבעת המסתם המיטרלי מסויידת, אי ספיקה מיטרלית קלה, אי ספיקה טריקוספידלית מינימלית, לחץ דם ריאתי מוגבר במידה בינונית עד קשה, תבנית מילוי פסוידו נורמלית. יחסE/E' מתאים ללחצי מילוי מוגברים בחדר שמאל. נוזל פריקרדיאלי מינימלי.  ", ' חדר שמאלי בגודל תקין תפקודו הגלובלי הסיסטולי  תקין עם היפוקנזיה אינפרובזלית וספטובזלית , תבניתץ מילוי דיאסטולי לא ניתנת להערכה מדוייקת על פי קריטריונים חדשים של ASE.    חדר ימין בגודל ותפקוד תקינים   עליה שמאלית מורחבת במידה קלה    מסתם אאורטלי עם דלף מנימלי   מסתם מיטרלי עם דלף קל    דלף טריקוספידלי קל    לחץ דם ראתי ססיטולי מוערך כמוגבר במידה קלה   וריד נבוב תחתון מורחב ואינו עובר תמט נשימתי באינספיריום   מודגם תפליט פריקרדיאלי קטן ללא אפקט הימודינמי   אאורטה עולה וסינוסים אאורטליים ברוחב תקין ', ' עליה שמאלתי מורחבת. חדר ימין היפוקינטי בינונית. חדרנ שמאל מורחב עם תפקוד גלובלי ירו במידה קשה. הספטום צלקתי ואקינטי. טרבקולציות בולטות באפקס של שני החדרים.( ? לCARDIAC NON COMPACTION) המערובות של חדר ימין בולטת. מסתם אורטלי  דו עלי , מעובה. דלף מיטרלי עד בינני. אס"ק טריקוספידלית קלה. אלקטרודת קוצב מימין.', 'איכות הדמיה מוגבלת   חדר שמאל בגודל תקין ,תפקודו הסיסטולי הגלובלי תקין ללא הפרעה אזורית , לא ניתן לקבוע תפקוד דיאסטולי,עליות בגודל תקין   חדר ימין בגודל ותפקוד תקינים ,לא ניתן להעריך ל"ד ריאתי בהעדר סיגנל TR   מבנה ותפקוד המסתמים תקין . ללא עדות לוגטציות בטכניקה זו (עם איכות הדמיה סבירה של המסתמים) '] |
| 12 | DEC-011 | whitespace_strip | MI: removed 174 whitespace-variant levels: [datetime.datetime(1981, 1, 1, 0, 0), datetime.datetime(1984, 1, 1, 0, 0), datetime.datetime(1987, 1, 1, 0, 0), datetime.datetime(1988, 1, 1, 0, 0), datetime.datetime(1991, 1, 1, 0, 0)] |
| 13 | DEC-012 | no_value_to_nan | LeftVentricleCavitySize: 45 "No Value" -> NaN |
| 14 | DEC-012 | no_value_to_nan | LeftVentricleWallThickness: 143 "No Value" -> NaN |
| 15 | DEC-012 | no_value_to_nan | LeftVentricleSystolicFunction: 46 "No Value" -> NaN |
| 16 | DEC-012 | no_value_to_nan | RVSize: 195 "No Value" -> NaN |
| 17 | DEC-012 | no_value_to_nan | RVSystolicFunction: 194 "No Value" -> NaN |
| 18 | DEC-012 | no_value_to_nan | LACavitySize: 29 "No Value" -> NaN |
| 19 | DEC-012 | no_value_to_nan | AorticValveStructure: 106 "No Value" -> NaN |
| 20 | DEC-012 | no_value_to_nan | AorticValveRegurgitation: 156 "No Value" -> NaN |
| 21 | DEC-012 | no_value_to_nan | MitralValveStructure: 261 "No Value" -> NaN |
| 22 | DEC-012 | no_value_to_nan | MitralRegurgitation: 29 "No Value" -> NaN |
| 23 | DEC-012 | no_value_to_nan | TricuspidValveStructure: 339 "No Value" -> NaN |
| 24 | DEC-012 | no_value_to_nan | TricuspidRegurgitation: 26 "No Value" -> NaN |
| 25 | DEC-014 | see_below_to_nan | LeftVentricleWallThickness: 6 "See below" -> NaN |
| 26 | DEC-014 | see_below_to_nan | AorticValveStructure: 1 "See below" -> NaN |
| 27 | DEC-014 | see_below_to_nan | MitralValveStructure: 5 "See below" -> NaN |
| 28 | DEC-018 | preserved_to_normal | LeftVentricleSystolicFunction: 58 "Preserved" -> "Normal" |
| 29 | DEC-019 | mr_english_to_roman | MR: 6× "Trace" -> "Trivial" |
| 30 | DEC-019 | mr_english_to_roman | MR: 9× "Mild" -> "Mild (I)" |
| 31 | DEC-019 | mr_english_to_roman | MR: 3× "Moderate" -> "Moderate (II)" |
| 32 | DEC-019 | mr_english_to_roman | MR: 2× "Severe" -> "Severe (IV)" |
| 33 | — | comorb_null_to_binary | MI -> MI_binary (n_pos=193, 29.9%) |
| 34 | — | comorb_null_to_binary | CABG -> CABG_binary (n_pos=133, 20.6%) |
| 35 | — | comorb_null_to_binary | IHD -> IHD_binary (n_pos=396, 61.4%) |
| 36 | — | comorb_null_to_binary | AFIB -> AFIB_binary (n_pos=303, 47.0%) |
| 37 | — | comorb_null_to_binary | HTN -> HTN_binary (n_pos=533, 82.6%) |
| 38 | — | comorb_null_to_binary | Diabetes mellitus -> Diabetes mellitus_binary (n_pos=410, 63.6%) |
| 39 | — | comorb_null_to_binary | DYSLIPIDEMIA -> DYSLIPIDEMIA_binary (n_pos=311, 48.2%) |
| 40 | — | comorb_null_to_binary | COPD -> COPD_binary (n_pos=105, 16.3%) |
| 41 | — | comorb_null_to_binary | OncologicalDiagnosis -> OncologicalDiagnosis_binary (n_pos=143, 22.2%) |
| 42 | DEC-020 | working_censor_date | set to 2025-08-16 (provisional, pending source confirmation) |
| 43 | DEC-016 | echo_after_death_flag | 1 patient(s) with Echo_Date > DeathDate, flagged for exclusion |
| 44 | (derived from DEC-020) | derived_time_vars | gap_echo_to_dial_days, death_event, time_to_event_days, followup_days, died_1year |
| 45 | (naming consistency) | hosp_rename | "hospitalization-count" mirrored to "hosp_total" |
