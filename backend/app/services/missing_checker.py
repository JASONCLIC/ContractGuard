REQUIRED_BY_TYPE = {
    "labor": [
        {
            "key": ["salary", "wage", "remuneration", "compensation", "工资", "薪资"],
            "item_name": "Salary / Remuneration",
            "description": "No clause clearly specifying salary amount or payment terms was detected.",
            "potential_risk": "Without a defined salary, the employer may delay or reduce payment without clear recourse.",
        },
        {
            "key": ["work location", "place of work", "working address", "工作地点", "办公地点"],
            "item_name": "Work Location",
            "description": "No clause specifying the work location was detected.",
            "potential_risk": "Absence of a stated work location may allow the employer to unilaterally relocate the employee.",
        },
        {
            "key": ["contract term", "term of employment", "duration", "合同期限"],
            "item_name": "Contract Term",
            "description": "No clause defining the contract duration was detected.",
            "potential_risk": "An undefined term creates ambiguity over the length of employment and renewal rights.",
        },
        {
            "key": ["dispute", "arbitration", "governing law", "争议"],
            "item_name": "Dispute Resolution",
            "description": "No dispute resolution clause was detected.",
            "potential_risk": "Without a dispute resolution mechanism, resolving conflicts may be costly and time-consuming.",
        },
        {
            "key": ["terminat", "dismiss", "解除", "终止"],
            "item_name": "Termination Conditions",
            "description": "No clause outlining the conditions for termination was detected.",
            "potential_risk": "Unclear termination conditions increase the risk of wrongful dismissal disputes.",
        },
        {
            "key": ["working hours", "work hours", "overtime", "工作时间"],
            "item_name": "Working Hours",
            "description": "No clause specifying working hours or overtime arrangements was detected.",
            "potential_risk": "Undefined working hours may lead to excessive unpaid overtime.",
        },
        {
            "key": ["breach", "liquidated damages", "penalty", "违约"],
            "item_name": "Breach Liability",
            "description": "No breach of contract liability clause was detected.",
            "potential_risk": "Without breach provisions, enforcing contractual obligations may be difficult.",
        },
    ],
    "internship": [
        {
            "key": ["stipend", "allowance", "补贴", "实习工资"],
            "item_name": "Stipend / Allowance",
            "description": "No clause specifying a stipend or allowance was detected.",
            "potential_risk": "Without a defined stipend, the intern may receive no compensation.",
        },
        {
            "key": ["internship period", "internship duration", "实习期限"],
            "item_name": "Internship Duration",
            "description": "No clause defining the internship period was detected.",
            "potential_risk": "An undefined duration may leave the intern without a clear end date.",
        },
        {
            "key": ["supervisor", "mentor", "指导老师", "导师"],
            "item_name": "Supervisor / Mentor",
            "description": "No clause designating a supervisor or mentor was detected.",
            "potential_risk": "Lack of supervision arrangements may affect the quality of the internship experience.",
        },
        {
            "key": ["dispute", "arbitration", "争议"],
            "item_name": "Dispute Resolution",
            "description": "No dispute resolution clause was detected.",
            "potential_risk": "Without a dispute resolution mechanism, resolving conflicts may be difficult.",
        },
        {
            "key": ["work location", "place of work", "工作地点"],
            "item_name": "Work Location",
            "description": "No clause specifying the work location was detected.",
            "potential_risk": "An unstated work location may allow unilateral changes without notice.",
        },
    ],
    "service": [
        {
            "key": ["fee", "remuneration", "payment", "报酬", "服务费"],
            "item_name": "Service Fee / Remuneration",
            "description": "No clause specifying the service fee or payment terms was detected.",
            "potential_risk": "Without defined payment terms, recovering fees may require litigation.",
        },
        {
            "key": ["scope of service", "services to be provided", "服务内容"],
            "item_name": "Scope of Services",
            "description": "No clause defining the scope of services was detected.",
            "potential_risk": "An undefined scope of work creates the risk of scope creep and disputes over deliverables.",
        },
        {
            "key": ["breach", "liquidated damages", "penalty", "违约"],
            "item_name": "Breach Liability",
            "description": "No breach of contract liability clause was detected.",
            "potential_risk": "Without breach provisions, enforcing obligations may be difficult.",
        },
        {
            "key": ["dispute", "arbitration", "governing law", "争议"],
            "item_name": "Dispute Resolution",
            "description": "No dispute resolution clause was detected.",
            "potential_risk": "Without a dispute resolution mechanism, resolving conflicts may be costly.",
        },
        {
            "key": ["terminat", "termination procedure", "终止流程"],
            "item_name": "Termination Procedure",
            "description": "No clause outlining the procedure for terminating the service agreement was detected.",
            "potential_risk": "The absence of termination procedures may lead to abrupt contract endings without proper notice.",
        },
    ],
}


def detect_missing_items(clauses, contract_type):
    text_blob = "\n".join(c["content"] for c in clauses).lower()
    required = REQUIRED_BY_TYPE.get(contract_type, REQUIRED_BY_TYPE["labor"])
    missing = []
    for field in required:
        if not any(k.lower() in text_blob for k in field["key"]):
            missing.append(
                {
                    "item_name": field["item_name"],
                    "description": field["description"],
                    "potential_risk": field["potential_risk"],
                }
            )
    return missing
