import json
if __name__=="__main__":
	output = open("output.txt",'w')
	dictOrder = {}
	with open("DBinsectidentificationJSON2.txt",'r') as f:
		for line in f:
			print(line)
			dictOrder[json.loads(line)['Order']] = "https://www.inaturalist.org/observations/export?q="+json.loads(line)['Order']+"&quality_grade=any&identifications=any&iconic_taxa%5B%5D=Arachnida&iconic_taxa%5B%5D=Insecta&place_id=97394&rank=species&verifiable=true&d1=2022-10-01&d2=2023-06-09&spam=false"+"\n"
		for val in dictOrder.values():
			output.write(val)

	output.flush()
	output.close()
