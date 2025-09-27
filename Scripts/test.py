from datamule import Index

index = Index()
results = index.search_submissions(
    submission_type="SCHEDULE 13D",
    requests_per_second=3,

)
print(results)
