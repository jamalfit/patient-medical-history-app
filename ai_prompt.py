def get_medical_report_prompt(patient_data):
    return f"""
    As an AI medical assistant, provide a comprehensive medical report for the following patient. Your report must include detailed information for ALL of the following sections:

    1. ASA Physical Status Classification:
       - Determine the ASA class (I-VI) based on the patient's overall health status.
       - Provide a brief explanation for the classification.

    2. Medication Analysis:
       - List all current medications.
       - Identify potential drug interactions or side effects.
       - Suggest any necessary adjustments or additional medications.

    3. Medical Evaluation:
       - Assess each reported medical condition and its current status.
       - Evaluate how the medical history impacts the patient's current health.
       - Consider the impact of BMI on the patient's health.

    4. Recommendations:
       - Suggest specific tests or consultations based on the patient's conditions.
       - Recommend lifestyle changes or interventions to improve health.
       - Propose a follow-up schedule if necessary.

    5. Risk Assessment:
       - Identify potential health risks based on the patient's profile.
       - Assess the likelihood and severity of these risks.
       - Suggest preventive measures for identified risks.

    6. Additional Notes:
       - Provide any other relevant observations or concerns.
       - Highlight areas where more information might be needed for a complete assessment.

    Use medical terminology appropriately, but ensure the report is clear and understandable. Be thorough and specific in your analysis for each section.

    Patient Information:
    - Age: {patient_data['age']}
    - BMI: {patient_data['bmi']}
    - Current Medications: {patient_data['current_meds']}
    - Allergies: {patient_data['allergies']}
    - Medical Conditions: {patient_data['medical_conditions']}
    - Medical History: {patient_data['medical_history']}

    Structure your response with clear section headers for each of the six areas mentioned above. Ensure that you provide substantial information for each section, not just the BMI analysis.
    """