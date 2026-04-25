import sys
import asyncio
from pathlib import Path

# Thêm thư mục src vào sys.path để Python nhận diện được package reviewagent
sys.path.insert(0, str(Path(__file__).parent / "src"))

from reviewagent.connectors.crossref import CrossrefConnector

async def main():
    # Một mã DOI nổi tiếng (Bài báo về AlphaFold trên tạp chí Nature)
    test_doi = "10.1038/s41586-020-2649-2" 
    
    print(f"Dang ket noi toi Crossref de tim DOI: {test_doi}...")
    
    # Sử dụng 'async with' để tận dụng Context Manager (tự động đóng kết nối khi xong)
    async with CrossrefConnector() as connector:
        result = await connector.lookup(test_doi)
        
        if result:
            print("\nTHANH CONG! Duoi day la du lieu da duoc chuan hoa (CMS):")
            # In ra dưới dạng JSON format cho dễ nhìn
            print(result.model_dump_json(indent=2))
        else:
            print("\nKhong tim thay bai bao hoac co loi xay ra.")

if __name__ == "__main__":
    asyncio.run(main())
