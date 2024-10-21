def generate_medical_report(patient_data):
    logger.debug("Generating medical report using Gemini Pro model")
    try:
        prompt = get_medical_report_prompt(patient_data)
        logger.debug(f"Prompt sent to Gemini: {prompt}")
        
        model = GenerativeModel("gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": 4096,
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 40
            }
        )
        
        logger.debug(f"Raw response from Gemini: {response}")
        if response.text:
            logger.debug(f"Processed text from Gemini: {response.text}")
            return response.text
        else:
            logger.error("Gemini returned an empty response")
            return "Error: Gemini returned an empty response"
    except Exception as e:
        logger.error(f"Error generating medical report: {str(e)}")
        return f"Error generating report: {str(e)}"

@app.route('/process_form', methods=['POST'])
def process_form():
    logger.debug("Processing patient form")
    try:
        name = request.form.get('name')
        age = int(request.form.get('age'))
        height = float(request.form.get('height'))
        weight = float(request.form.get('weight'))
        current_meds = request.form.get('current_meds')
        allergies = request.form.get('allergies')
        medical_conditions = request.form.get('medical_conditions')
        medical_history = request.form.get('medical_history')
        email = session.get('user_email')
        
        bmi = calculate_bmi(height, weight)
        
        patient_data = {
            "age": age,
            "bmi": bmi,
            "current_meds": current_meds,
            "allergies": allergies,
            "medical_conditions": medical_conditions,
            "medical_history": medical_history
        }
        
        ai_response = generate_medical_report(patient_data)
        logger.debug(f"AI Response: {ai_response}")
        
        # Parse the AI response
        sections = {
            "ASA Physical Status Classification": "",
            "Medication Analysis": "",
            "Medical Evaluation": "",
            "Recommendations": "",
            "Risk Assessment": "",
            "Additional Notes": ""
        }

        if "Error" in ai_response:
            for section in sections:
                sections[section] = "Error generating this section. Please try again."
        else:
            current_section = None
            for line in ai_response.split('\n'):
                if any(section in line for section in sections.keys()):
                    current_section = next(section for section in sections.keys() if section in line)
                elif current_section:
                    sections[current_section] += line + '\n'

        for section, content in sections.items():
            logger.debug(f"{section}: {content[:100]}...")  # Log first 100 chars of each section

        logger.debug("Form processed successfully, rendering result")
        return render_template('result.html', 
                               name=name, 
                               age=age, 
                               height=height, 
                               weight=weight, 
                               bmi=bmi,
                               current_meds=current_meds,
                               allergies=allergies,
                               medical_conditions=medical_conditions,
                               medical_history=medical_history,
                               email=email,
                               **sections)
    except Exception as e:
        logger.error(f"Error processing form: {str(e)}")
        return jsonify({"error": "An error occurred while processing the form"}), 500