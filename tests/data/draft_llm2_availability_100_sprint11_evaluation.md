# Sprint 11 — Draft Evaluation Report

**Pipeline version:** `sprint11`  
**Run at:** 2026-06-09 07:34:13 UTC  
**Source fixture:** `availability_fixture_100.json`  
**Prompt version:** v6  
**Warmth model:** `claude-haiku-4-5-20251001`

---

## Summary

| Metric | Value |
|---|---|
| Total records | 100 |
| Full LLM calls | 0 |
| Warmth LLM calls attempted | 25 |
| Warmth sentences accepted | 25 |
| Warmth sentences dropped | 0 |
| Deterministic calls | 100 |
| Menu hallucinations | 0 |
| Special-touches hallucinations | 0 |
| Booking-form hallucinations | 0 |
| Total hallucinations | 0 |
| Auto-send eligible | 100/100 (100.0%) |
| Warmth tokens | 4,264 in / 471 out |

---

## Pipeline Changes (S11)

- RESP-023: RESPOND_UNAVAILABLE deterministic — no LLM call
- RESP-036: ACKNOWLEDGE_AND_CHECK_AVAILABILITY deterministic — no LLM call
- RESP-037: confirm_available_next_step copy block (strict next step)
- RESP-038: CONFIRM_AVAILABLE fully deterministic + optional warmth LLM
- RESP-039: warmth LLM — max 1 sentence, max 20 words
- RESP-040: WarmthSentenceValidator — warmth dropped on any violation
- RESP-041: raw guest message NOT passed to warmth LLM

---

## Email Evaluations

### #001 — email_01

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Dinner for next Friday  
**From:** Amy Harris &lt;amy.harris@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hi, do you have availability next Friday for dinner for 8? It’s for my sister’s birthday. Around 7ish would be ideal, but we can be flexible if needed. Thanks, Amy

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-12 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your eight guests.*  → ACCEPTED ✅

> Dear Amy,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-06-12.  
> We're delighted to celebrate this special birthday with you and your eight guests.  
>   
> Please note that our mandatory minimum spend for this space is £1,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #002 — email_02

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Table on the 20th  
**From:** Martin Lewis &lt;martin.lewis@gmail.com&gt;  
**Domain:** `gmail.com`

> Hello, I’m trying to book dinner on the 20th for a group of 10. It’s for my dad’s birthday, nothing too formal, just a nice evening meal. Do you have anything from 7pm?

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-20 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Martin,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-06-20.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #003 — email_03

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch next month  
**From:** Priya Shah &lt;priya.shah@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hi there, could you do lunch on the 20th of next month for 12 people? We’re planning a baby shower and would prefer something around midday if possible. Thanks, Priya

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-20 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Priya,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-07-20.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #004 — email_04

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Any weekend this month  
**From:** Chris Porter &lt;chris.porter@outlook.com&gt;  
**Domain:** `outlook.com`

> Hello, we’re looking for dinner for 14 people for an engagement party, any weekend this month if you have space. Evening would be best but we’re open. Thanks, Chris

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-06 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *How wonderful to celebrate your engagement with fourteen loved ones over dinner!*  → ACCEPTED ✅

> Dear Chris,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-06-06.  
> How wonderful to celebrate your engagement with fourteen loved ones over dinner!  
>   
> Please note that our mandatory minimum spend for this space is £1,400.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #005 — email_05

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Weekend next month  
**From:** Hannah Mills &lt;hannah.mills@btinternet.com&gt;  
**Domain:** `btinternet.com`

> Hi, do you have availability for lunch for 8 for a babyshower on any weekend next month? Morning or midday could work, depending on what you have. Best, Hannah

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-04 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *How wonderful to celebrate this special baby shower with your loved ones!*  → ACCEPTED ✅

> Dear Hannah,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-07-04.  
> How wonderful to celebrate this special baby shower with your loved ones!  
>   
> Please note that our mandatory minimum spend for this space is £520.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #006 — email_06

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** July 25 dinner  
**From:** Claire Dawson &lt;claire.dawson@smithconsulting.co.uk&gt;  
**Domain:** `smithconsulting.co.uk`

> Good afternoon, I’d like to enquire about dinner on July 25 for a group of 16. It’s for an engagement party. Around 8pm would be great if available.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-25 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Claire,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-07-25.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #007 — email_07

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Jul 25 birthday  
**From:** Tom Bennett &lt;tom.bennett@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, can you fit 9 of us for Jul 25? It’s my friend’s birthday and we’d like dinner, maybe early evening around 6. Thanks!

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Tom,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-25 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #008 — email_08

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** 7/25 reservation  
**From:** Sarah Green &lt;sarah.green@aol.com&gt;  
**Domain:** `aol.com`

> Hello, looking to book for 11 people on 7/25 for dinner. It’s a surprise birthday, probably 7:30pm if that works.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Sarah,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-25 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #009 — email_09

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Last Friday of the month  
**From:** James Carter &lt;james.carter@icloud.com&gt;  
**Domain:** `icloud.com`

> Hi there, do you have space for the last Friday of the month for 10 people? It’s for an engagement dinner. Later dinner would suit us best.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-26 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear James,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-06-26.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #010 — email_10

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Breakfast next Saturday  
**From:** Mark Stevens &lt;mark.stevens@live.co.uk&gt;  
**Domain:** `live.co.uk`

> Morning, I’m organising a birthday breakfast next Saturday for 6 people. Something in the morning would be ideal, but I don’t have an exact time yet.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-13 |
| Meal period | breakfast |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Mark,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for breakfast on 2026-06-13.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #011 — email_11

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch tomorrow week  
**From:** Nadia Khan &lt;nadia.khan@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, can you do lunch for 8 a week tomorrow? It’s for a small baby shower. Midday-ish would be lovely if possible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-11 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Nadia,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-06-11.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #012 — email_12

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Dinner on 25/7  
**From:** Emily Watts &lt;emily.watts@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hello, we’re hoping to book dinner on 25/7 for 18 guests for an engagement party. We can do 7 or 8pm depending on availability.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Emily,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-25 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #013 — email_13

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Any Friday in August  
**From:** Rob Evans &lt;rob.evans@google.com&gt;  
**Domain:** `google.com`

> Hi, I’m looking for dinner for a birthday for 12 people, any Friday in August would work. We’d prefer evening but can be flexible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-07 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your twelve guests!*  → ACCEPTED ✅

> Dear Rob,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-08-07.  
> We're delighted to celebrate this special birthday with you and your twelve guests!  
>   
> Please note that our mandatory minimum spend for this space is £1,200.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #014 — email_14

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** First Saturday in July  
**From:** Aisha Ahmed &lt;aisha.ahmed@deloitte.com&gt;  
**Domain:** `deloitte.com`

> Hi, do you have dinner availability for 15 people on the first Saturday in July? It’s for a babyshower celebration, although dinner rather than lunch.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-04 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special moment with you and your fifteen guests.*  → ACCEPTED ✅

> Dear Aisha,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-07-04.  
> We're delighted to celebrate this special moment with you and your fifteen guests.  
>   
> Please note that our mandatory minimum spend for this space is £1,500.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #015 — email_15

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Morning booking  
**From:** Laura King &lt;laura.king@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hello, can I book something in the morning on June 18 for 10 people? It’s for a birthday breakfast, but we haven’t fixed the exact time yet.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-18 |
| Meal period | breakfast |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your group!*  → ACCEPTED ✅

> Dear Laura,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for breakfast on 2026-06-18.  
> We're delighted to celebrate this special birthday with you and your group!  
>   
> Please note that our mandatory minimum spend for this space is £350.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #016 — email_16

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Midday lunch enquiry  
**From:** Ben Cooper &lt;ben.cooper@barclays.co.uk&gt;  
**Domain:** `barclays.co.uk`

> Hi there, looking for a table at midday on 8 July for a group of 7. It’s for a small engagement lunch. Could you let me know availability?

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-08 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *How wonderful to celebrate your engagement with those closest to you!*  → ACCEPTED ✅

> Dear Ben,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-07-08.  
> How wonderful to celebrate your engagement with those closest to you!  
>   
> Please note that our mandatory minimum spend for this space is £500.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #017 — email_17

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Next Friday or Saturday  
**From:** Sophie Turner &lt;sophie.turner@proton.me&gt;  
**Domain:** `proton.me`

> Hi, do you have dinner space for 20 people next Friday or Saturday? It’s for a joint birthday. We’ll take whichever night has better availability.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Sophie,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-06-12 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #018 — email_18

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Monday to Wednesday next three weeks  
**From:** Rebecca Lane &lt;rebecca.lane@kpmg.com&gt;  
**Domain:** `kpmg.com`

> Hello, I need lunch for a baby shower for 9 guests, any Monday to Wednesday in the next three weeks. Midday would be preferred but not essential.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-08 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Rebecca,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-06-08.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #019 — email_19

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** On 14/6 dinner  
**From:** Omar Ali &lt;omar.ali@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, we’re looking to book dinner on 14/6 for 8 people. It’s an engagement party, just close friends and family.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-14 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Omar,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-06-14.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #020 — email_20

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous 7/6  
**From:** Neil Brooks &lt;neil.brooks@unknownmail.co.uk&gt;  
**Domain:** `unknownmail.co.uk`

> Hi, could you book dinner for 10 on 7/6? It’s for a birthday. I’m not sure how you read the date format so please check if needed.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Neil,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-06-07 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #021 — email_21

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** The Sunday after next  
**From:** Yasmin Begum &lt;yasmin.begum@btinternet.com&gt;  
**Domain:** `btinternet.com`

> Hi there, do you have lunch for 13 people the Sunday after next? It’s for a baby shower and we’d probably arrive around midday.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-14 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Yasmin,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-06-14.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #022 — email_22

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** This Friday breakfast  
**From:** Peter Walsh &lt;peter.walsh@icloud.com&gt;  
**Domain:** `icloud.com`

> Hello, can we book breakfast this Friday for 5 people? It’s a birthday breakfast, probably morning but we can confirm the time later.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-05 |
| Meal period | breakfast |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your loved ones.*  → ACCEPTED ✅

> Dear Peter,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for breakfast on 2026-06-05.  
> We're delighted to celebrate this special birthday with you and your loved ones.  
>   
> Please note that our mandatory minimum spend for this space is £250.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #023 — email_23

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** End of July  
**From:** Lara Stone &lt;lara.stone@eventsbylara.com&gt;  
**Domain:** `eventsbylara.com`

> Hi, I’m arranging an engagement dinner for around 12 people at the end of July. Ideally a Friday or Saturday night if you have anything.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-24 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Lara,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-07-24.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #024 — email_24

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch 06/20  
**From:** Fiona Blake &lt;fiona.blake@amazon.com&gt;  
**Domain:** `amazon.com`

> Hi, do you have lunch available on 06/20 for a group of 6? It’s for my mum’s birthday. Midday or early afternoon is fine.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-20 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your five guests!*  → ACCEPTED ✅

> Dear Fiona,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-06-20.  
> We're delighted to celebrate this special birthday with you and your five guests!  
>   
> Please note that our mandatory minimum spend for this space is £500.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #025 — email_25

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Breakfast on the 15th  
**From:** George Miller &lt;george.miller@gmail.com&gt;  
**Domain:** `gmail.com`

> Good morning, I’m looking for breakfast on the 15th for 8 people. It’s for a small office birthday breakfast, sometime in the morning.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-15 |
| Meal period | breakfast |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your eight guests!*  → ACCEPTED ✅

> Dear George,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for breakfast on 2026-06-15.  
> We're delighted to celebrate this special birthday with you and your eight guests!  
>   
> Please note that our mandatory minimum spend for this space is £280.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #026 — email_26

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Next month first weekend  
**From:** Natalie Price &lt;natalie.price@microsoft.com&gt;  
**Domain:** `microsoft.com`

> Hello, could you let me know availability for dinner for 14 on the first weekend next month? It’s for an engagement party.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Natalie,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #027 — email_27

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Tomorrow dinner  
**From:** Daniel Wood &lt;daniel.wood@aol.com&gt;  
**Domain:** `aol.com`

> Hi, can you fit 10 people tomorrow for dinner? It’s a last-minute birthday meal. We’d be looking for around 7pm if possible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-04 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Daniel,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-06-04.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #028 — email_28

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Two weeks today  
**From:** Maya Singh &lt;maya.singh@accenture.com&gt;  
**Domain:** `accenture.com`

> Hi there, I’d like to book lunch for 11 people two weeks today. It’s for a babyshower and midday would be great.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-17 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special baby shower moment with you and your guests.*  → ACCEPTED ✅

> Dear Maya,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-06-17.  
> We're delighted to celebrate this special baby shower moment with you and your guests.  
>   
> Please note that our mandatory minimum spend for this space is £715.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #029 — email_29

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** July 4 morning  
**From:** Oliver Reed &lt;oliver.reed@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hello, do you have anything on July 4 in the morning for 7 people? It’s a birthday breakfast but we can be flexible on exact time.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-04 |
| Meal period | breakfast |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Oliver,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for breakfast on 2026-07-04.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #030 — email_30

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Mid August dinner  
**From:** Elena Rossi &lt;elena.rossi@jpmorgan.com&gt;  
**Domain:** `jpmorgan.com`

> Hi, we need dinner for an engagement party for 16 people sometime in mid August, ideally a weekend. Please let me know options.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-15 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate your engagement with you and your sixteen guests this evening.*  → ACCEPTED ✅

> Dear Elena,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-08-15.  
> We're delighted to celebrate your engagement with you and your sixteen guests this evening.  
>   
> Please note that our mandatory minimum spend for this space is £1,600.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #031 — email_31

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** On 9/1 ambiguous  
**From:** Sam Roberts &lt;sam.roberts@smallbusiness.co.uk&gt;  
**Domain:** `smallbusiness.co.uk`

> Hi, can you do dinner for 9 on 9/1? It’s for a birthday. I’m writing dates the American way, if that helps.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-09-01 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your nine guests this evening.*  → ACCEPTED ✅

> Dear Sam,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-09-01.  
> We're delighted to celebrate this special birthday with you and your nine guests this evening.  
>   
> Please note that our mandatory minimum spend for this space is £1,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #032 — email_32

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch on 1/9 ambiguous  
**From:** Megan Clark &lt;megan.clark@gmail.com&gt;  
**Domain:** `gmail.com`

> Hello, we want lunch for 10 on 1/9 for a baby shower. I mean UK format, 1 September. Midday if possible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-09-01 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special baby shower moment with you and your guests.*  → ACCEPTED ✅

> Dear Megan,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-09-01.  
> We're delighted to celebrate this special baby shower moment with you and your guests.  
>   
> Please note that our mandatory minimum spend for this space is £650.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #033 — email_33

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Next Thursday evening  
**From:** Helen Cross &lt;helen.cross@executiveoffice.co.uk&gt;  
**Domain:** `executiveoffice.co.uk`

> Hi, do you have dinner availability next Thursday for a group of 8? It’s for an engagement dinner and we’d like evening if possible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-11 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate your engagement with you and your closest loved ones.*  → ACCEPTED ✅

> Dear Helen,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-06-11.  
> We're delighted to celebrate your engagement with you and your closest loved ones.  
>   
> Please note that our mandatory minimum spend for this space is £1,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #034 — email_34

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Any lunch this week  
**From:** Connor Murphy &lt;connor.murphy@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hi, is there any lunch availability this week for 6 people? It’s for a small birthday. Around midday, but we can do another lunchtime slot.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-03 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Connor,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-06-03.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #035 — email_35

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Last Saturday in August  
**From:** Amelia Fox &lt;amelia.fox@sohohouse.com&gt;  
**Domain:** `sohohouse.com`

> Hello, I’m trying to book dinner for 18 on the last Saturday in August. It’s for an engagement party. Later evening preferred.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-29 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Amelia,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-08-29.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #036 — email_36

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Breakfast next Monday  
**From:** Rachel Adams &lt;rachel.adams@googlemail.com&gt;  
**Domain:** `googlemail.com`

> Hi, could we book breakfast next Monday for 4 people? It’s a small birthday breakfast. Morning is fine, exact time flexible.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-08 |
| Meal period | breakfast |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your loved ones.*  → ACCEPTED ✅

> Dear Rachel,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for breakfast on 2026-06-08.  
> We're delighted to celebrate this special birthday with you and your loved ones.  
>   
> Please note that our mandatory minimum spend for this space is £250.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #037 — email_37

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Weekend around July 18  
**From:** Dan White &lt;dan.white@btopenworld.com&gt;  
**Domain:** `btopenworld.com`

> Hi, do you have dinner for 12 people the weekend around July 18? It’s a baby shower dinner, probably Saturday if available but Sunday could work.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-18 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Dan,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-07-18.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #038 — email_38

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** On the 3rd of next month  
**From:** Clara Hughes &lt;clara.hughes@familyholdings.com&gt;  
**Domain:** `familyholdings.com`

> Hi, can we reserve lunch on the 3rd of next month for 8? It’s for an engagement celebration, nothing huge. Midday would be ideal.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-03 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *How wonderful to celebrate your engagement with those closest to you!*  → ACCEPTED ✅

> Dear Clara,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-07-03.  
> How wonderful to celebrate your engagement with those closest to you!  
>   
> Please note that our mandatory minimum spend for this space is £520.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #039 — email_39

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Any morning next week  
**From:** Tina Brown &lt;tina.brown@ivygroup.co.uk&gt;  
**Domain:** `ivygroup.co.uk`

> Hello, I’m looking for a birthday breakfast for 10 people any morning next week. We don’t mind which weekday if there is availability.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Tina,  
>   
> Thank you for your enquiry — I'll check availability for breakfast on 2026-06-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #040 — email_40

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Early September lunch  
**From:** Vik Patel &lt;vik.patel@londonbusinessgroup.com&gt;  
**Domain:** `londonbusinessgroup.com`

> Hi, could you send availability for lunch for 15 people in early September? It’s for a baby shower. Midday or early afternoon would work.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Vik,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-09-01 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #041 — email_41

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Engagment diner enquiry  
**From:** Amy Harris &lt;amy.harris@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hello, do you have space for an engagment diner for 14 on the last Friday of August? Thinking 7pm but can shift a bit. Thanks, Lara

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-28 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Amy,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-08-28.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #042 — email_42

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Baby shower lunch  
**From:** Martin Lewis &lt;martin.lewis@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, I am looking for lunch for a babyshower on the 20th of next month for 12 people. Midday would be perfect if you have any space. Many thanks, Priya

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Martin,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-20 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #043 — email_43

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Breakfast after graduation  
**From:** Priya Shah &lt;priya.shah@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Morning, could you do brekfast for 10 of us on July 3rd? It is for my daughter’s graduation day and we would like something in the morning, maybe around 9. Cheers, Mark

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-03 |
| Meal period | breakfast |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this wonderful graduation milestone with you and your group.*  → ACCEPTED ✅

> Dear Priya,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for breakfast on 2026-07-03.  
> We're delighted to celebrate this wonderful graduation milestone with you and your group.  
>   
> Please note that our mandatory minimum spend for this space is £350.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #044 — email_44

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Any Friday in July  
**From:** Chris Porter &lt;chris.porter@outlook.com&gt;  
**Domain:** `outlook.com`

> Hi there, we need a table for 8 for a leaving do. Any Friday in July would work, preferably dinner time. Could you let me know what dates are free? Thanks, Sophie

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-03 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Chris,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-07-03.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #045 — email_45

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch for christning  
**From:** Hannah Mills &lt;hannah.mills@btinternet.com&gt;  
**Domain:** `btinternet.com`

> Hello, do you have availability for a christning lunch for 18 people between 11th and 13th July? We can do any of those days around 1pm. Regards, Nadia

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-11 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special christening with you and your eighteen guests.*  → ACCEPTED ✅

> Dear Hannah,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-07-11.  
> We're delighted to celebrate this special christening with you and your eighteen guests.  
>   
> Please note that our mandatory minimum spend for this space is £1,170.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #046 — email_46

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Hens diner  
**From:** Claire Dawson &lt;claire.dawson@smithconsulting.co.uk&gt;  
**Domain:** `smithconsulting.co.uk`

> Hi, I’m trying to sort a hen do diner for 16 girls on 7/25 if you have availability. Later evening would be great, around 8.30. Thanks!! Emily

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Claire,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-25 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #047 — email_47

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Bday brunch  
**From:** Tom Bennett &lt;tom.bennett@gmail.com&gt;  
**Domain:** `gmail.com`

> Hey, have you got brunch for 6 next Sunday? It’s for my brother’s bday. Morning-ish is fine, maybe 10 or 11. Thanks, Josh

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-14 |
| Meal period | breakfast |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Tom,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for breakfast on 2026-06-14.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #048 — email_48

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Team meal next Weds  
**From:** Sarah Green &lt;sarah.green@aol.com&gt;  
**Domain:** `aol.com`

> Hi, can I book for a work team meal next Weds for 11 people? Not sure if lunch or early dinner is better, probably around 4ish. One person is vegetarian. Thanks, Helen

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-10 |
| Meal period | dinner |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Sarah,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for dinner on 2026-06-10.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #049 — email_49

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Mums birthday  
**From:** James Carter &lt;james.carter@icloud.com&gt;  
**Domain:** `icloud.com`

> Hello, I need dinner for 9 on the 15th for my mum’s 70th birthday. I mean this month if possible. Around 6:30 please. Thanks, Aaron

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-15 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your nine guests this evening.*  → ACCEPTED ✅

> Dear James,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-06-15.  
> We're delighted to celebrate this special birthday with you and your nine guests this evening.  
>   
> Please note that our mandatory minimum spend for this space is £1,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #050 — email_50

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Anniversary meal  
**From:** Mark Stevens &lt;mark.stevens@live.co.uk&gt;  
**Domain:** `live.co.uk`

> Hi, would you have a table for 4 for an anniversery dinner on 07/08? I’m not sure if you read that as July or August — I mean 7 August. Around 7pm. Thanks, Clara

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Mark,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-07 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #051 — email_51

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Private party maybe September  
**From:** Nadia Khan &lt;nadia.khan@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, looking for a small private party for 20 people the first weekend of September. It’s an engagement / family celebration. Dinner or drinks and food would be fine. Thanks, Rob

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-09-05 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate your engagement with you and your twenty guests this evening.*  → ACCEPTED ✅

> Dear Nadia,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-09-05.  
> We're delighted to celebrate your engagement with you and your twenty guests this evening.  
>   
> Please note that our mandatory minimum spend for this space is £2,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #052 — email_52

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Lunch next month  
**From:** Emily Watts &lt;emily.watts@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Good afternoon, do you have a room for 10 pp for lunch any Monday to Wednesday in July? This is for a small client thank-you meal. Midday or early afternoon is ok. Kind regards, Martin

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-01 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Emily,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-07-01.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #053 — email_53

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** School reunion  
**From:** Rob Evans &lt;rob.evans@google.com&gt;  
**Domain:** `google.com`

> Hi there, we are organising a school reunion diner for approx 22 on Saturday 18 July. Do you have anything after 7? Thanks, Becky

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Rob,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-18 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #054 — email_54

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Baby shower any weekend next month  
**From:** Aisha Ahmed &lt;aisha.ahmed@deloitte.com&gt;  
**Domain:** `deloitte.com`

> Hello, I’m arranging a baby shower for 15 ladies. Any weekend next month could work, ideally lunch. Could you send options please? Thanks, Amira

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Aisha,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #055 — email_55

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Date maybe ambiguous  
**From:** Laura King &lt;laura.king@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hi, do you have diner for 8 on 9/8? It’s for a promotion celebration. I’m not sure if that is clear in your system. Around 8pm please. Thanks, Neil

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Laura,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-09 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #056 — email_56

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Miday birthday lunch  
**From:** Ben Cooper &lt;ben.cooper@barclays.co.uk&gt;  
**Domain:** `barclays.co.uk`

> Hi, can you fit 13 of us on 30 June for a birthday lunch? Miday would be best, sorry I mean around 12. Thanks, Fran

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-30 |
| Meal period | lunch |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your thirteen guests!*  → ACCEPTED ✅

> Dear Ben,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for lunch on 2026-06-30.  
> We're delighted to celebrate this special birthday with you and your thirteen guests!  
>   
> Please note that our mandatory minimum spend for this space is £845.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #057 — email_57

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Breakfast meeting  
**From:** Sophie Turner &lt;sophie.turner@proton.me&gt;  
**Domain:** `proton.me`

> Good morning, I need to book a breakfast meeting for 7 on the 24th of this month. Morning, maybe 8am or 8.30. It’s a board meeting. Regards, Elaine

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-24 |
| Meal period | breakfast |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Sophie,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for breakfast on 2026-06-24.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #058 — email_58

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Birthday end of month  
**From:** Rebecca Lane &lt;rebecca.lane@kpmg.com&gt;  
**Domain:** `kpmg.com`

> Hey, do you have a table for 10 at the end of this month for my flatmate’s birthday? Dinner ideally but dates are flexible, maybe the last Sat or Sun. Cheers, Dan

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-27 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special birthday with you and your guests.*  → ACCEPTED ✅

> Dear Rebecca,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-06-27.  
> We're delighted to celebrate this special birthday with you and your guests.  
>   
> Please note that our mandatory minimum spend for this space is £1,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #059 — email_59

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Corporate lunch Friday  
**From:** Omar Ali &lt;omar.ali@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, I’m booking on behalf of my director. Can you do lunch for 12 next Friday for a client workshop? Around midday, nothing too formal. Best, Jessica, EA

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-06-12 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Omar,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-06-12.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #060 — email_60

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Family get together  
**From:** Neil Brooks &lt;neil.brooks@unknownmail.co.uk&gt;  
**Domain:** `unknownmail.co.uk`

> Hello, looking for dinner for 18 for a family get together on Aug 14th. Early evening preferred, around 6. Can you advise availability? Thanks, Monica

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-14 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to welcome your family of eighteen for a special dinner together.*  → ACCEPTED ✅

> Dear Neil,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-08-14.  
> We're delighted to welcome your family of eighteen for a special dinner together.  
>   
> Please note that our mandatory minimum spend for this space is £1,800.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #061 — email_61

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous 6/8 dinner  
**From:** Yasmin Begum &lt;yasmin.begum@btinternet.com&gt;  
**Domain:** `btinternet.com`

> Hi, can you do dinner for 10 on 6/8? It’s for a birthday meal. I’m using slash dates and not sure if that’s clear. Around 7 would be ideal. Thanks, Mia

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Yasmin,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-06 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #062 — email_62

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** US date format lunch  
**From:** Peter Walsh &lt;peter.walsh@icloud.com&gt;  
**Domain:** `icloud.com`

> Hello, could I book lunch for 12 on 8/6? I mean American format, August 6. It’s for a client thank-you lunch, ideally midday. Regards, Alan

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-06 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Peter,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-08-06.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #063 — email_63

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** UK date format baby shower  
**From:** Lara Stone &lt;lara.stone@eventsbylara.com&gt;  
**Domain:** `eventsbylara.com`

> Hi, I’m looking for a baby shower lunch for 14 on 8/6, UK format, so 8 June. Midday or early afternoon please. Thanks, Leila

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Lara,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-06-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #064 — email_64

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Birthday on 4/7  
**From:** Fiona Blake &lt;fiona.blake@amazon.com&gt;  
**Domain:** `amazon.com`

> Hey, do you have dinner for 8 on 4/7? It’s my partner’s birthday and I realise the date might be read two ways. Around 8pm if possible. Thanks, Nina

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Fiona,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #065 — email_65

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** US July 4 celebration  
**From:** George Miller &lt;george.miller@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi there, can I book dinner for 9 on 7/4? I mean July 4 in US date format. It’s for a small Independence Day get together. Thanks, Sam

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear George,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #066 — email_66

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Promotion dinner unclear date  
**From:** Natalie Price &lt;natalie.price@microsoft.com&gt;  
**Domain:** `microsoft.com`

> Hello, do you have availability for a promotion diner for 11 on 5/8? I’m not sure if your system reads that as May or August. Around 7:30 please. Thanks, Omar

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Natalie,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-05 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #067 — email_67

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Anniversary lunch 05/08  
**From:** Daniel Wood &lt;daniel.wood@aol.com&gt;  
**Domain:** `aol.com`

> Hi, could you fit 6 for lunch on 05/08? I mean 5 August. It’s for an anniversery lunch and midday would be ideal.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-08-05 |
| Meal period | lunch |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Daniel,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for lunch on 2026-08-05.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #068 — email_68

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Christening lunch ambiguous  
**From:** Maya Singh &lt;maya.singh@accenture.com&gt;  
**Domain:** `accenture.com`

> Hello, do you have a room for 18 pp for christening lunch on 11/7? I mean the date as I’ve written it, but please confirm if unclear. Around 1pm. Thanks, Iman

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Maya,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-11 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #069 — email_69

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Baby shower US typed  
**From:** Oliver Reed &lt;oliver.reed@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hi, I’m organising a baby shower for 15 on 7/11. Sorry, that’s US format for July 11. Lunch would be best. Thanks, Noor

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Oliver,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-11 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #070 — email_70

**Goal:** `CONFIRM AVAILABLE`  **Generation:** `deterministic+warmth`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Leaving do UK date  
**From:** Elena Rossi &lt;elena.rossi@jpmorgan.com&gt;  
**Domain:** `jpmorgan.com`

> Hi there, we need dinner for 20 on 10/7, UK format so 10 July. It’s for a leaving do. Ideally after 7pm. Cheers, Matt

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-07-10 |
| Meal period | dinner |
| Status | `available` |

#### Draft Response

**Rule:** `RESP-038`  **Path:** `deterministic+warmth`

**Warmth sentence:** *We're delighted to celebrate this special farewell with you and your twenty guests this evening.*  → ACCEPTED ✅

> Dear Elena,  
>   
> Thank you for your enquiry — I'm delighted to confirm that we have availability for dinner on 2026-07-10.  
> We're delighted to celebrate this special farewell with you and your twenty guests this evening.  
>   
> Please note that our mandatory minimum spend for this space is £2,000.  
>   
> Please reply to this email to confirm you would like to proceed, and our events team will be in touch to finalise the booking.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #071 — email_71

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous 7/10 dinner  
**From:** Sam Roberts &lt;sam.roberts@smallbusiness.co.uk&gt;  
**Domain:** `smallbusiness.co.uk`

> Hello, could you check dinner availability for 12 on 7/10? It’s for an engagement party and I’m not sure if that date is clear. Evening please. Thanks, Chloe

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Sam,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-10-07 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #072 — email_72

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Morning meeting 6/9  
**From:** Megan Clark &lt;megan.clark@gmail.com&gt;  
**Domain:** `gmail.com`

> Good morning, could we book breakfast for 7 on 6/9? It’s a board meeting. Date format might be ambiguous, so please confirm. Around 8.30. Regards, Eva

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Megan,  
>   
> Thank you for your enquiry — I'll check availability for breakfast on 2026-09-06 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #073 — email_73

**Goal:** `RESPOND UNAVAILABLE`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** US morning meeting  
**From:** Helen Cross &lt;helen.cross@executiveoffice.co.uk&gt;  
**Domain:** `executiveoffice.co.uk`

> Hi, can you do breakfast for 7 on 9/6? I mean US format, September 6. It’s for a board meeting, morning slot please.

#### Availability Context

| Field | Value |
|---|---|
| Restaurant | The Grand Ballroom |
| Room | The Mayfair Suite |
| Date | 2026-09-06 |
| Meal period | breakfast |
| Status | `booked` |

#### Draft Response

**Rule:** `RESP-023`  **Path:** `deterministic`

> Dear Helen,  
>   
> Thank you for your enquiry. Unfortunately, we are fully booked for breakfast on 2026-09-06.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #074 — email_74

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Graduation dinner ambiguous  
**From:** Connor Murphy &lt;connor.murphy@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hi, looking for dinner for 13 on 3/7 for a graduation meal. I’m UK based so I mean day/month if that helps. Around 6:30. Thanks, Rachel

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Connor,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-03 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #075 — email_75

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous family meal  
**From:** Amelia Fox &lt;amelia.fox@sohohouse.com&gt;  
**Domain:** `sohohouse.com`

> Hello, I’d like dinner for 16 on 8/9 for a family get together. I’m not sure whether you use UK or US dates. Around 7pm please. Thanks, Tony

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Amelia,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-09-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #076 — email_76

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Birthday brunch 09/08  
**From:** Rachel Adams &lt;rachel.adams@googlemail.com&gt;  
**Domain:** `googlemail.com`

> Hey, have you got brunch for 8 on 09/08? I mean 9 August, UK style. It’s for my sister’s bday, morning-ish. Thanks, Ellie

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Rachel,  
>   
> Thank you for your enquiry — I'll check availability for breakfast on 2026-08-09 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #077 — email_77

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Client dinner 08/09 US  
**From:** Dan White &lt;dan.white@btopenworld.com&gt;  
**Domain:** `btopenworld.com`

> Good afternoon, I need dinner for 10 on 08/09, using US format for August 9. This is a client dinner. Around 7.30 if possible. Best, Michael

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Dan,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-09 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #078 — email_78

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Retirement lunch ambiguous  
**From:** Clara Hughes &lt;clara.hughes@familyholdings.com&gt;  
**Domain:** `familyholdings.com`

> Hi, could you fit 12 for a retirement lunch on 2/9? It may be ambiguous but we are in the UK. Midday if available. Thanks, Paula

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Clara,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-09-02 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #079 — email_79

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Work celebration unclear  
**From:** Tina Brown &lt;tina.brown@ivygroup.co.uk&gt;  
**Domain:** `ivygroup.co.uk`

> Hi, can you do dinner for 14 on 10/8? It’s a work celebration. I’m not sure if that will be read as October or August, so please check. Thanks, Greg

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Tina,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-10 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #080 — email_80

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Baby naming lunch  
**From:** Vik Patel &lt;vik.patel@londonbusinessgroup.com&gt;  
**Domain:** `londonbusinessgroup.com`

> Hello, I’m arranging a baby naming lunch for 17 on 12/7. We are UK based, so I mean 12 July. Around 12:30 would be perfect. Thanks, Yasmin

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Vik,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-12 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #081 — email_81

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Private dining enquiry - 29 June  
**From:** Olivia Grant &lt;olivia@londoneventcollective.co.uk&gt;  
**Domain:** `londoneventcollective.co.uk`

> Hi there, please can you help with a new private dining enquiry? My client is looking for a private dinner on Monday 29th June 2026 for 12 guests, arriving from 19:00 and finishing around 23:00. Budget has not yet been advised. Please confirm minimum numbers, maximum numbers, access times, where pre-dinner drinks are served, whether a set or choice menu is available, any room hire, minimum spend, service charge, drinks prices and whether you offer agency commission. Thank you, Olivia

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Olivia,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-06-29 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #082 — email_82

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Agency enquiry for client dinner  
**From:** James Porter &lt;james@eventsourceagency.com&gt;  
**Domain:** `eventsourceagency.com`

> Good afternoon, I am working on behalf of a corporate client who needs dinner for 18 guests on 4/7. UK format, so 4 July. Arrival would be 18:30 with dinner from 19:00. Could you send private dining rates, minimum spend, room hire, menus, wine packages, service charge and commission terms? Kind regards, James

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear James,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #083 — email_83

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** PA request for board dinner  
**From:** Rebecca Hall &lt;rebecca.hall@microsoft.com&gt;  
**Domain:** `microsoft.com`

> Hello, I am the PA to our Managing Director and I am looking to arrange a board dinner for 10 guests next Thursday. Please could you confirm availability, minimum spend, whether a pre-order is required and whether the room has a screen or private area? Dinner would be from 7pm. Best, Rebecca

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Rebecca,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-06-11 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #084 — email_84

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Private office lunch  
**From:** Anna Wilkes &lt;anna@privateoffice-london.co.uk&gt;  
**Domain:** `privateoffice-london.co.uk`

> Dear team, I am booking on behalf of a private family office. They would like lunch for 14 guests on 8/7. Please treat this as UK format, 8 July. Could you confirm availability, private room options, minimum and maximum numbers, menu choices, access times and service charge? Commission is not required. Regards, Anna

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Anna,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #085 — email_85

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Agency commission question  
**From:** Zoe Miller &lt;zoe@prestigeeventpartners.co.uk&gt;  
**Domain:** `prestigeeventpartners.co.uk`

> Hi, my client is considering a dinner for 22 on 8/7 but I am not sure which date format your system uses. We are UK based so we would mean 8 July. Please send rates, packages, minimum spend, room hire, pre-order deadlines, cancellation terms and agency commission. Arrival about 7pm. Many thanks, Zoe

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Zoe,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #086 — email_86

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** EA dinner enquiry  
**From:** Helen Morris &lt;helen.morris@google.com&gt;  
**Domain:** `google.com`

> Hello, I am the EA to our CEO. Could you check dinner availability for 8 people on Friday 31 July? We would like a private or semi-private space from 19:30. Please confirm room hire, minimum spend, menu options and whether drinks can be served before dinner. Best wishes, Helen

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Helen,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-31 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #087 — email_87

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Concierge client birthday  
**From:** Marcus Lee &lt;marcus@eliteconcierge.co.uk&gt;  
**Domain:** `eliteconcierge.co.uk`

> Hi, I am arranging this for a concierge client. They need a birthday dinner for 16 guests on 11/8. Please provisionally check UK format, 11 August, and advise if you need date confirmation. Can you send minimum spend, menus, drinks packages, service charge and commission options? Thanks, Marcus

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Marcus,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-11 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #088 — email_88

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Product launch lunch  
**From:** Melissa Carter &lt;melissa.carter@salesforce.com&gt;  
**Domain:** `salesforce.com`

> Good morning, I am an events manager organising a product launch lunch for 24 guests on any Monday to Wednesday in the last two weeks of July. Please confirm suitable rooms, capacities, minimum spend, AV availability, menu choices, room hire and access times. Kind regards, Melissa

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Melissa,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-20 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #089 — email_89

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Agency dinner VEI  
**From:** Chloe Evans &lt;chloe@venuesandeventsintl.com&gt;  
**Domain:** `venuesandeventsintl.com`

> Hi, please can you help with a new private dining enquiry for my client? They are looking for dinner on 15/8 for 12 guests, 19:00 to 22:30. Please send rates, minimum numbers, maximum numbers, menus, wine from prices, soft drink prices, room hire, minimum spend and confirm if agency commission is available. Many thanks, Chloe

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Chloe,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-15 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #090 — email_90

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Assistant booking anniversary  
**From:** Lily Fraser &lt;lily.fraser@executiveoffice.co.uk&gt;  
**Domain:** `executiveoffice.co.uk`

> Hello, I am booking on behalf of Mr and Mrs Carter for an anniversary dinner for 6 on 3/9. We are using UK date format, so 3 September. Please confirm if a quiet table or private area is available and send any set menu options. Kind regards, Lily, Personal Assistant

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Lily,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-09-03 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #091 — email_91

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous 4/7 dinner  
**From:** Ellie Moore &lt;ellie.moore@gmail.com&gt;  
**Domain:** `gmail.com`

> Hi, do you have dinner for 10 on 4/7? It is for my birthday. I am in London so I mean 4 July, but please check if needed. Around 7pm would be ideal. Thanks, Ellie

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Ellie,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-07-04 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #092 — email_92

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** US style date  
**From:** Maya Thompson &lt;maya.thompson@yahoo.com&gt;  
**Domain:** `yahoo.com`

> Hello, I’m visiting from New York and would like dinner for 8 on 8/7. I mean August 7, American style. It’s for an engagement celebration. Could we do around 8pm? Thanks, Maya

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Maya,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-07 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #093 — email_93

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Unclear numeric date  
**From:** Laura Knight &lt;laura.knight@hotmail.com&gt;  
**Domain:** `hotmail.com`

> Hi there, could you do lunch for 9 on 5/7? It is for a baby shower. I am not sure how your system reads dates. Midday would be ideal.

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Laura,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-05 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #094 — email_94

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Corporate team meal  
**From:** Ryan Walsh &lt;ryan.walsh@deloitte.com&gt;  
**Domain:** `deloitte.com`

> Hi, can you arrange dinner for 15 on 21 August for a project completion meal? I’m from Deloitte but this is just a team dinner, not an agency booking. Around 6:30 would be good. Thanks, Ryan

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Ryan,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-21 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #095 — email_95

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Possible agency domain  
**From:** Emma Rice &lt;emma@eventsbyemma.com&gt;  
**Domain:** `eventsbyemma.com`

> Hi, I’m Emma from Events by Emma. I’m helping my friend plan her birthday dinner for 12 on the first Friday of August. Could you tell me availability and any minimum spend? No commission needed. Thanks, Emma

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Emma,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-08-07 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #096 — email_96

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Unknown consulting domain  
**From:** Paul Green &lt;paul@greenconsulting.co.uk&gt;  
**Domain:** `greenconsulting.co.uk`

> Hello, do you have availability for lunch for 10 on 10/7? UK format, 10 July. It is a client thank-you meal. Please send menu options and whether a semi-private area is possible. Regards, Paul

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Paul,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-07-10 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #097 — email_97

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ambiguous no clue  
**From:** Gareth Owen &lt;gareth.owen@aol.com&gt;  
**Domain:** `aol.com`

> Hi, looking for dinner for 11 on 8/9 for a promotion celebration. Not sure if that date is clear. Around 7.30 if you have space. Thanks, Gareth

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Gareth,  
>   
> Thank you for your enquiry — I'll check availability for dinner on 2026-09-08 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #098 — email_98

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Ivygroup confusion  
**From:** Sofia Lane &lt;sofia@ivygroupconsulting.com&gt;  
**Domain:** `ivygroupconsulting.com`

> Hi, I work with Ivy Group Consulting and would like breakfast for 6 on 24/6 for an investor meeting. Could you confirm availability around 8am and any minimum spend? Best, Sofia

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Sofia,  
>   
> Thank you for your enquiry — I'll check availability for breakfast on 2026-06-24 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> James

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #099 — email_99

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Family celebration public domain  
**From:** Patrick Nolan &lt;patrick.nolan@btinternet.com&gt;  
**Domain:** `btinternet.com`

> Hello, can you do lunch for 20 on the weekend of 22 August? It’s a family reunion. Saturday would be best but Sunday also works. Thanks, Patrick

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Patrick,  
>   
> Thank you for your enquiry — I'll check availability for lunch on 2026-08-22 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Eleanor

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---

### #100 — email_100

**Goal:** `ACKNOWLEDGE & CHECK`  **Generation:** `deterministic`  **Verdict:** ✅ AUTO-SEND ELIGIBLE

#### Inbound Email

**Subject:** Agency breakfast briefing  
**From:** Daniel Scott &lt;daniel@corporatehospitality.co.uk&gt;  
**Domain:** `corporatehospitality.co.uk`

> Good morning, we are sourcing venues for a client breakfast briefing for 25 guests on 2/9. Please assume UK date format, 2 September. We need arrival from 08:00, presentation screen, coffee, breakfast menu, rates, minimum spend, room hire, access from time and commission terms. Kind regards, Daniel

#### Availability Context

*Not checked — awaiting availability confirmation.*

#### Draft Response

**Rule:** `RESP-036`  **Path:** `deterministic`

> Dear Daniel,  
>   
> Thank you for your enquiry — I'll check availability for breakfast on 2026-09-02 and come back to you shortly.  
>   
> I will check availability and follow up with you as soon as possible.  
>   
> Warm regards,  
> Sophia

#### Evaluation

- ✅ PASS — Menu mention
- ✅ PASS — Special touches
- ✅ PASS — Booking form reference

**Auto-send:** ✅ ELIGIBLE

---
