# AdventureWorks2022 데이터 구조

이 문서는 로컬 Docker SQL Server에 복원한 `AdventureWorks2022`의 시스템 카탈로그를 직접 조회해 생성한 데이터 구조 스냅샷이다. 행 수는 2026-07-14 기준이며, 업무 데이터가 변경되면 달라질 수 있다.

## 1. 데이터베이스 개요

| 항목 | 값 |
|---|---:|
| 데이터베이스 | `AdventureWorks2022` |
| SQL Server 버전 | `16.0.4255.1` |
| 에디션 | Developer Edition (64-bit) |
| 업무 스키마 | 6개 |
| 테이블 | 71개 |
| 컬럼 | 486개 |
| 전체 행 | 760,837행 |
| Primary Key 제약 | 71개 |
| Foreign Key 제약 | 90개 |
| Unique 제약 | 1개 |
| Check 제약 | 89개 |
| 사용자 View | 20개 |

행 수는 전체 테이블을 `COUNT(*)`로 스캔하지 않고 `sys.dm_db_partition_stats`의 heap/clustered index 메타데이터를 합산했다.

## 2. 업무 도메인 구조

- `Person`: 개인·법인 식별자, 이름, 주소, 이메일, 전화번호와 연락 유형
- `HumanResources`: 직원, 부서, 직무, 급여 및 부서 이동 이력
- `Production`: 제품, 카테고리, 모델, BOM, 재고, 생산 작업과 트랜잭션
- `Purchasing`: 공급업체, 공급 제품, 구매 주문과 배송 방법
- `Sales`: 고객, 매장, 영업 담당자, 판매 주문, 프로모션, 통화와 카드
- `dbo`: 빌드 버전, 데이터베이스 변경 로그와 오류 로그

대표적인 업무 흐름:

- `Person.Person` → `Sales.Customer` → `Sales.SalesOrderHeader` → `Sales.SalesOrderDetail` → `Production.Product`
- `Purchasing.Vendor` → `Purchasing.ProductVendor` → `Production.Product`
- `Production.Product` → `Production.BillOfMaterials` / `Production.WorkOrder` / `Production.ProductInventory`

## 3. 스키마별 규모

| 스키마 | 테이블 | 컬럼 | 행 수 |
|---|---:|---:|---:|
| `HumanResources` | 6 | 40 | 934 |
| `Person` | 13 | 70 | 141,250 |
| `Production` | 25 | 169 | 349,895 |
| `Purchasing` | 5 | 49 | 13,426 |
| `Sales` | 19 | 137 | 253,735 |
| `dbo` | 3 | 21 | 1,597 |

## 4. 행 수가 큰 테이블

| 순위 | 테이블 | 행 수 | 컬럼 수 |
|---:|---|---:|---:|
| 1 | `Sales.SalesOrderDetail` | 121,317 | 11 |
| 2 | `Production.TransactionHistory` | 113,443 | 9 |
| 3 | `Production.TransactionHistoryArchive` | 89,253 | 9 |
| 4 | `Production.WorkOrder` | 72,591 | 10 |
| 5 | `Production.WorkOrderRouting` | 67,131 | 12 |
| 6 | `Sales.SalesOrderHeader` | 31,465 | 26 |
| 7 | `Sales.SalesOrderHeaderSalesReason` | 27,647 | 3 |
| 8 | `Person.BusinessEntity` | 20,777 | 3 |
| 9 | `Person.EmailAddress` | 19,972 | 5 |
| 10 | `Person.Password` | 19,972 | 5 |
| 11 | `Person.Person` | 19,972 | 13 |
| 12 | `Person.PersonPhone` | 19,972 | 4 |
| 13 | `Sales.Customer` | 19,820 | 7 |
| 14 | `Person.Address` | 19,614 | 9 |
| 15 | `Person.BusinessEntityAddress` | 19,614 | 5 |

## 5. 전체 테이블 카탈로그

| 테이블 | 행 수 | 컬럼 | Primary Key | 나가는 FK | 들어오는 FK |
|---|---:|---:|---|---:|---:|
| `dbo.AWBuildVersion` | 1 | 4 | `[SystemInformationID]` | 0 | 0 |
| `dbo.DatabaseLog` | 1,596 | 8 | `[DatabaseLogID]` | 0 | 0 |
| `dbo.ErrorLog` | 0 | 9 | `[ErrorLogID]` | 0 | 0 |
| `HumanResources.Department` | 16 | 4 | `[DepartmentID]` | 0 | 1 |
| `HumanResources.Employee` | 290 | 16 | `[BusinessEntityID]` | 1 | 6 |
| `HumanResources.EmployeeDepartmentHistory` | 296 | 6 | `[BusinessEntityID], [StartDate], [DepartmentID], [ShiftID]` | 3 | 0 |
| `HumanResources.EmployeePayHistory` | 316 | 5 | `[BusinessEntityID], [RateChangeDate]` | 1 | 0 |
| `HumanResources.JobCandidate` | 13 | 4 | `[JobCandidateID]` | 1 | 0 |
| `HumanResources.Shift` | 3 | 5 | `[ShiftID]` | 0 | 1 |
| `Person.Address` | 19,614 | 9 | `[AddressID]` | 1 | 3 |
| `Person.AddressType` | 6 | 4 | `[AddressTypeID]` | 0 | 1 |
| `Person.BusinessEntity` | 20,777 | 3 | `[BusinessEntityID]` | 0 | 5 |
| `Person.BusinessEntityAddress` | 19,614 | 5 | `[BusinessEntityID], [AddressID], [AddressTypeID]` | 3 | 0 |
| `Person.BusinessEntityContact` | 909 | 5 | `[BusinessEntityID], [PersonID], [ContactTypeID]` | 3 | 0 |
| `Person.ContactType` | 20 | 3 | `[ContactTypeID]` | 0 | 1 |
| `Person.CountryRegion` | 238 | 3 | `[CountryRegionCode]` | 0 | 3 |
| `Person.EmailAddress` | 19,972 | 5 | `[BusinessEntityID], [EmailAddressID]` | 1 | 0 |
| `Person.Password` | 19,972 | 5 | `[BusinessEntityID]` | 1 | 0 |
| `Person.Person` | 19,972 | 13 | `[BusinessEntityID]` | 1 | 7 |
| `Person.PersonPhone` | 19,972 | 4 | `[BusinessEntityID], [PhoneNumber], [PhoneNumberTypeID]` | 2 | 0 |
| `Person.PhoneNumberType` | 3 | 3 | `[PhoneNumberTypeID]` | 0 | 1 |
| `Person.StateProvince` | 181 | 8 | `[StateProvinceID]` | 2 | 2 |
| `Production.BillOfMaterials` | 2,679 | 9 | `[BillOfMaterialsID]` | 3 | 0 |
| `Production.Culture` | 8 | 3 | `[CultureID]` | 0 | 1 |
| `Production.Document` | 13 | 14 | `[DocumentNode]` | 1 | 1 |
| `Production.Illustration` | 5 | 3 | `[IllustrationID]` | 0 | 1 |
| `Production.Location` | 14 | 5 | `[LocationID]` | 0 | 2 |
| `Production.Product` | 504 | 25 | `[ProductID]` | 4 | 14 |
| `Production.ProductCategory` | 4 | 4 | `[ProductCategoryID]` | 0 | 1 |
| `Production.ProductCostHistory` | 395 | 5 | `[ProductID], [StartDate]` | 1 | 0 |
| `Production.ProductDescription` | 762 | 4 | `[ProductDescriptionID]` | 0 | 1 |
| `Production.ProductDocument` | 32 | 3 | `[ProductID], [DocumentNode]` | 2 | 0 |
| `Production.ProductInventory` | 1,069 | 7 | `[ProductID], [LocationID]` | 2 | 0 |
| `Production.ProductListPriceHistory` | 395 | 5 | `[ProductID], [StartDate]` | 1 | 0 |
| `Production.ProductModel` | 128 | 6 | `[ProductModelID]` | 0 | 3 |
| `Production.ProductModelIllustration` | 7 | 3 | `[ProductModelID], [IllustrationID]` | 2 | 0 |
| `Production.ProductModelProductDescriptionCulture` | 762 | 4 | `[ProductModelID], [ProductDescriptionID], [CultureID]` | 3 | 0 |
| `Production.ProductPhoto` | 101 | 6 | `[ProductPhotoID]` | 0 | 1 |
| `Production.ProductProductPhoto` | 504 | 4 | `[ProductID], [ProductPhotoID]` | 2 | 0 |
| `Production.ProductReview` | 4 | 8 | `[ProductReviewID]` | 1 | 0 |
| `Production.ProductSubcategory` | 37 | 5 | `[ProductSubcategoryID]` | 1 | 1 |
| `Production.ScrapReason` | 16 | 3 | `[ScrapReasonID]` | 0 | 1 |
| `Production.TransactionHistory` | 113,443 | 9 | `[TransactionID]` | 1 | 0 |
| `Production.TransactionHistoryArchive` | 89,253 | 9 | `[TransactionID]` | 0 | 0 |
| `Production.UnitMeasure` | 38 | 3 | `[UnitMeasureCode]` | 0 | 4 |
| `Production.WorkOrder` | 72,591 | 10 | `[WorkOrderID]` | 2 | 1 |
| `Production.WorkOrderRouting` | 67,131 | 12 | `[WorkOrderID], [ProductID], [OperationSequence]` | 2 | 0 |
| `Purchasing.ProductVendor` | 460 | 11 | `[ProductID], [BusinessEntityID]` | 3 | 0 |
| `Purchasing.PurchaseOrderDetail` | 8,845 | 11 | `[PurchaseOrderID], [PurchaseOrderDetailID]` | 2 | 0 |
| `Purchasing.PurchaseOrderHeader` | 4,012 | 13 | `[PurchaseOrderID]` | 3 | 1 |
| `Purchasing.ShipMethod` | 5 | 6 | `[ShipMethodID]` | 0 | 2 |
| `Purchasing.Vendor` | 104 | 8 | `[BusinessEntityID]` | 1 | 2 |
| `Sales.CountryRegionCurrency` | 109 | 3 | `[CountryRegionCode], [CurrencyCode]` | 2 | 0 |
| `Sales.CreditCard` | 19,118 | 6 | `[CreditCardID]` | 0 | 2 |
| `Sales.Currency` | 105 | 3 | `[CurrencyCode]` | 0 | 3 |
| `Sales.CurrencyRate` | 13,532 | 7 | `[CurrencyRateID]` | 2 | 1 |
| `Sales.Customer` | 19,820 | 7 | `[CustomerID]` | 3 | 1 |
| `Sales.PersonCreditCard` | 19,118 | 3 | `[BusinessEntityID], [CreditCardID]` | 2 | 0 |
| `Sales.SalesOrderDetail` | 121,317 | 11 | `[SalesOrderID], [SalesOrderDetailID]` | 2 | 0 |
| `Sales.SalesOrderHeader` | 31,465 | 26 | `[SalesOrderID]` | 8 | 2 |
| `Sales.SalesOrderHeaderSalesReason` | 27,647 | 3 | `[SalesOrderID], [SalesReasonID]` | 2 | 0 |
| `Sales.SalesPerson` | 17 | 9 | `[BusinessEntityID]` | 2 | 4 |
| `Sales.SalesPersonQuotaHistory` | 163 | 5 | `[BusinessEntityID], [QuotaDate]` | 1 | 0 |
| `Sales.SalesReason` | 10 | 4 | `[SalesReasonID]` | 0 | 1 |
| `Sales.SalesTaxRate` | 29 | 7 | `[SalesTaxRateID]` | 1 | 0 |
| `Sales.SalesTerritory` | 10 | 10 | `[TerritoryID]` | 1 | 5 |
| `Sales.SalesTerritoryHistory` | 17 | 6 | `[BusinessEntityID], [StartDate], [TerritoryID]` | 2 | 0 |
| `Sales.ShoppingCartItem` | 3 | 6 | `[ShoppingCartItemID]` | 1 | 0 |
| `Sales.SpecialOffer` | 16 | 11 | `[SpecialOfferID]` | 0 | 1 |
| `Sales.SpecialOfferProduct` | 538 | 4 | `[SpecialOfferID], [ProductID]` | 2 | 1 |
| `Sales.Store` | 701 | 6 | `[BusinessEntityID]` | 2 | 1 |

## 6. 전체 Foreign Key 관계

복합 FK는 컬럼 대응을 쉼표로 묶어 하나의 제약으로 표시한다. AdventureWorks의 FK 동작은 기본적으로 `NO_ACTION`이다.

| FK 이름 | 출발 테이블 | 도착 테이블 | 컬럼 대응 | 삭제 | 갱신 |
|---|---|---|---|---|---|
| `FK_Employee_Person_BusinessEntityID` | `HumanResources.Employee` | `Person.Person` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_EmployeeDepartmentHistory_Department_DepartmentID` | `HumanResources.EmployeeDepartmentHistory` | `HumanResources.Department` | DepartmentID → DepartmentID | `NO_ACTION` | `NO_ACTION` |
| `FK_EmployeeDepartmentHistory_Employee_BusinessEntityID` | `HumanResources.EmployeeDepartmentHistory` | `HumanResources.Employee` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_EmployeeDepartmentHistory_Shift_ShiftID` | `HumanResources.EmployeeDepartmentHistory` | `HumanResources.Shift` | ShiftID → ShiftID | `NO_ACTION` | `NO_ACTION` |
| `FK_EmployeePayHistory_Employee_BusinessEntityID` | `HumanResources.EmployeePayHistory` | `HumanResources.Employee` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_JobCandidate_Employee_BusinessEntityID` | `HumanResources.JobCandidate` | `HumanResources.Employee` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Address_StateProvince_StateProvinceID` | `Person.Address` | `Person.StateProvince` | StateProvinceID → StateProvinceID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityAddress_Address_AddressID` | `Person.BusinessEntityAddress` | `Person.Address` | AddressID → AddressID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityAddress_AddressType_AddressTypeID` | `Person.BusinessEntityAddress` | `Person.AddressType` | AddressTypeID → AddressTypeID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID` | `Person.BusinessEntityAddress` | `Person.BusinessEntity` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityContact_BusinessEntity_BusinessEntityID` | `Person.BusinessEntityContact` | `Person.BusinessEntity` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityContact_ContactType_ContactTypeID` | `Person.BusinessEntityContact` | `Person.ContactType` | ContactTypeID → ContactTypeID | `NO_ACTION` | `NO_ACTION` |
| `FK_BusinessEntityContact_Person_PersonID` | `Person.BusinessEntityContact` | `Person.Person` | PersonID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_EmailAddress_Person_BusinessEntityID` | `Person.EmailAddress` | `Person.Person` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Password_Person_BusinessEntityID` | `Person.Password` | `Person.Person` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Person_BusinessEntity_BusinessEntityID` | `Person.Person` | `Person.BusinessEntity` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_PersonPhone_Person_BusinessEntityID` | `Person.PersonPhone` | `Person.Person` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_PersonPhone_PhoneNumberType_PhoneNumberTypeID` | `Person.PersonPhone` | `Person.PhoneNumberType` | PhoneNumberTypeID → PhoneNumberTypeID | `NO_ACTION` | `NO_ACTION` |
| `FK_StateProvince_CountryRegion_CountryRegionCode` | `Person.StateProvince` | `Person.CountryRegion` | CountryRegionCode → CountryRegionCode | `NO_ACTION` | `NO_ACTION` |
| `FK_StateProvince_SalesTerritory_TerritoryID` | `Person.StateProvince` | `Sales.SalesTerritory` | TerritoryID → TerritoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_BillOfMaterials_Product_ComponentID` | `Production.BillOfMaterials` | `Production.Product` | ComponentID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_BillOfMaterials_Product_ProductAssemblyID` | `Production.BillOfMaterials` | `Production.Product` | ProductAssemblyID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_BillOfMaterials_UnitMeasure_UnitMeasureCode` | `Production.BillOfMaterials` | `Production.UnitMeasure` | UnitMeasureCode → UnitMeasureCode | `NO_ACTION` | `NO_ACTION` |
| `FK_Document_Employee_Owner` | `Production.Document` | `HumanResources.Employee` | Owner → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Product_ProductModel_ProductModelID` | `Production.Product` | `Production.ProductModel` | ProductModelID → ProductModelID | `NO_ACTION` | `NO_ACTION` |
| `FK_Product_ProductSubcategory_ProductSubcategoryID` | `Production.Product` | `Production.ProductSubcategory` | ProductSubcategoryID → ProductSubcategoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_Product_UnitMeasure_SizeUnitMeasureCode` | `Production.Product` | `Production.UnitMeasure` | SizeUnitMeasureCode → UnitMeasureCode | `NO_ACTION` | `NO_ACTION` |
| `FK_Product_UnitMeasure_WeightUnitMeasureCode` | `Production.Product` | `Production.UnitMeasure` | WeightUnitMeasureCode → UnitMeasureCode | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductCostHistory_Product_ProductID` | `Production.ProductCostHistory` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductDocument_Document_DocumentNode` | `Production.ProductDocument` | `Production.Document` | DocumentNode → DocumentNode | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductDocument_Product_ProductID` | `Production.ProductDocument` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductInventory_Location_LocationID` | `Production.ProductInventory` | `Production.Location` | LocationID → LocationID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductInventory_Product_ProductID` | `Production.ProductInventory` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductListPriceHistory_Product_ProductID` | `Production.ProductListPriceHistory` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductModelIllustration_Illustration_IllustrationID` | `Production.ProductModelIllustration` | `Production.Illustration` | IllustrationID → IllustrationID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductModelIllustration_ProductModel_ProductModelID` | `Production.ProductModelIllustration` | `Production.ProductModel` | ProductModelID → ProductModelID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductModelProductDescriptionCulture_Culture_CultureID` | `Production.ProductModelProductDescriptionCulture` | `Production.Culture` | CultureID → CultureID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductModelProductDescriptionCulture_ProductDescription_ProductDescriptionID` | `Production.ProductModelProductDescriptionCulture` | `Production.ProductDescription` | ProductDescriptionID → ProductDescriptionID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductModelProductDescriptionCulture_ProductModel_ProductModelID` | `Production.ProductModelProductDescriptionCulture` | `Production.ProductModel` | ProductModelID → ProductModelID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductProductPhoto_Product_ProductID` | `Production.ProductProductPhoto` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductProductPhoto_ProductPhoto_ProductPhotoID` | `Production.ProductProductPhoto` | `Production.ProductPhoto` | ProductPhotoID → ProductPhotoID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductReview_Product_ProductID` | `Production.ProductReview` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductSubcategory_ProductCategory_ProductCategoryID` | `Production.ProductSubcategory` | `Production.ProductCategory` | ProductCategoryID → ProductCategoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_TransactionHistory_Product_ProductID` | `Production.TransactionHistory` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_WorkOrder_Product_ProductID` | `Production.WorkOrder` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_WorkOrder_ScrapReason_ScrapReasonID` | `Production.WorkOrder` | `Production.ScrapReason` | ScrapReasonID → ScrapReasonID | `NO_ACTION` | `NO_ACTION` |
| `FK_WorkOrderRouting_Location_LocationID` | `Production.WorkOrderRouting` | `Production.Location` | LocationID → LocationID | `NO_ACTION` | `NO_ACTION` |
| `FK_WorkOrderRouting_WorkOrder_WorkOrderID` | `Production.WorkOrderRouting` | `Production.WorkOrder` | WorkOrderID → WorkOrderID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductVendor_Product_ProductID` | `Purchasing.ProductVendor` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductVendor_UnitMeasure_UnitMeasureCode` | `Purchasing.ProductVendor` | `Production.UnitMeasure` | UnitMeasureCode → UnitMeasureCode | `NO_ACTION` | `NO_ACTION` |
| `FK_ProductVendor_Vendor_BusinessEntityID` | `Purchasing.ProductVendor` | `Purchasing.Vendor` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_PurchaseOrderDetail_Product_ProductID` | `Purchasing.PurchaseOrderDetail` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_PurchaseOrderDetail_PurchaseOrderHeader_PurchaseOrderID` | `Purchasing.PurchaseOrderDetail` | `Purchasing.PurchaseOrderHeader` | PurchaseOrderID → PurchaseOrderID | `NO_ACTION` | `NO_ACTION` |
| `FK_PurchaseOrderHeader_Employee_EmployeeID` | `Purchasing.PurchaseOrderHeader` | `HumanResources.Employee` | EmployeeID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_PurchaseOrderHeader_ShipMethod_ShipMethodID` | `Purchasing.PurchaseOrderHeader` | `Purchasing.ShipMethod` | ShipMethodID → ShipMethodID | `NO_ACTION` | `NO_ACTION` |
| `FK_PurchaseOrderHeader_Vendor_VendorID` | `Purchasing.PurchaseOrderHeader` | `Purchasing.Vendor` | VendorID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Vendor_BusinessEntity_BusinessEntityID` | `Purchasing.Vendor` | `Person.BusinessEntity` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_CountryRegionCurrency_CountryRegion_CountryRegionCode` | `Sales.CountryRegionCurrency` | `Person.CountryRegion` | CountryRegionCode → CountryRegionCode | `NO_ACTION` | `NO_ACTION` |
| `FK_CountryRegionCurrency_Currency_CurrencyCode` | `Sales.CountryRegionCurrency` | `Sales.Currency` | CurrencyCode → CurrencyCode | `NO_ACTION` | `NO_ACTION` |
| `FK_CurrencyRate_Currency_FromCurrencyCode` | `Sales.CurrencyRate` | `Sales.Currency` | FromCurrencyCode → CurrencyCode | `NO_ACTION` | `NO_ACTION` |
| `FK_CurrencyRate_Currency_ToCurrencyCode` | `Sales.CurrencyRate` | `Sales.Currency` | ToCurrencyCode → CurrencyCode | `NO_ACTION` | `NO_ACTION` |
| `FK_Customer_Person_PersonID` | `Sales.Customer` | `Person.Person` | PersonID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Customer_SalesTerritory_TerritoryID` | `Sales.Customer` | `Sales.SalesTerritory` | TerritoryID → TerritoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_Customer_Store_StoreID` | `Sales.Customer` | `Sales.Store` | StoreID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_PersonCreditCard_CreditCard_CreditCardID` | `Sales.PersonCreditCard` | `Sales.CreditCard` | CreditCardID → CreditCardID | `NO_ACTION` | `NO_ACTION` |
| `FK_PersonCreditCard_Person_BusinessEntityID` | `Sales.PersonCreditCard` | `Person.Person` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderDetail_SalesOrderHeader_SalesOrderID` | `Sales.SalesOrderDetail` | `Sales.SalesOrderHeader` | SalesOrderID → SalesOrderID | `CASCADE` | `NO_ACTION` |
| `FK_SalesOrderDetail_SpecialOfferProduct_SpecialOfferIDProductID` | `Sales.SalesOrderDetail` | `Sales.SpecialOfferProduct` | SpecialOfferID → SpecialOfferID, ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_Address_BillToAddressID` | `Sales.SalesOrderHeader` | `Person.Address` | BillToAddressID → AddressID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_Address_ShipToAddressID` | `Sales.SalesOrderHeader` | `Person.Address` | ShipToAddressID → AddressID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_CreditCard_CreditCardID` | `Sales.SalesOrderHeader` | `Sales.CreditCard` | CreditCardID → CreditCardID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_CurrencyRate_CurrencyRateID` | `Sales.SalesOrderHeader` | `Sales.CurrencyRate` | CurrencyRateID → CurrencyRateID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_Customer_CustomerID` | `Sales.SalesOrderHeader` | `Sales.Customer` | CustomerID → CustomerID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_SalesPerson_SalesPersonID` | `Sales.SalesOrderHeader` | `Sales.SalesPerson` | SalesPersonID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_SalesTerritory_TerritoryID` | `Sales.SalesOrderHeader` | `Sales.SalesTerritory` | TerritoryID → TerritoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeader_ShipMethod_ShipMethodID` | `Sales.SalesOrderHeader` | `Purchasing.ShipMethod` | ShipMethodID → ShipMethodID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesOrderHeaderSalesReason_SalesOrderHeader_SalesOrderID` | `Sales.SalesOrderHeaderSalesReason` | `Sales.SalesOrderHeader` | SalesOrderID → SalesOrderID | `CASCADE` | `NO_ACTION` |
| `FK_SalesOrderHeaderSalesReason_SalesReason_SalesReasonID` | `Sales.SalesOrderHeaderSalesReason` | `Sales.SalesReason` | SalesReasonID → SalesReasonID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesPerson_Employee_BusinessEntityID` | `Sales.SalesPerson` | `HumanResources.Employee` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesPerson_SalesTerritory_TerritoryID` | `Sales.SalesPerson` | `Sales.SalesTerritory` | TerritoryID → TerritoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesPersonQuotaHistory_SalesPerson_BusinessEntityID` | `Sales.SalesPersonQuotaHistory` | `Sales.SalesPerson` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesTaxRate_StateProvince_StateProvinceID` | `Sales.SalesTaxRate` | `Person.StateProvince` | StateProvinceID → StateProvinceID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesTerritory_CountryRegion_CountryRegionCode` | `Sales.SalesTerritory` | `Person.CountryRegion` | CountryRegionCode → CountryRegionCode | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesTerritoryHistory_SalesPerson_BusinessEntityID` | `Sales.SalesTerritoryHistory` | `Sales.SalesPerson` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_SalesTerritoryHistory_SalesTerritory_TerritoryID` | `Sales.SalesTerritoryHistory` | `Sales.SalesTerritory` | TerritoryID → TerritoryID | `NO_ACTION` | `NO_ACTION` |
| `FK_ShoppingCartItem_Product_ProductID` | `Sales.ShoppingCartItem` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_SpecialOfferProduct_Product_ProductID` | `Sales.SpecialOfferProduct` | `Production.Product` | ProductID → ProductID | `NO_ACTION` | `NO_ACTION` |
| `FK_SpecialOfferProduct_SpecialOffer_SpecialOfferID` | `Sales.SpecialOfferProduct` | `Sales.SpecialOffer` | SpecialOfferID → SpecialOfferID | `NO_ACTION` | `NO_ACTION` |
| `FK_Store_BusinessEntity_BusinessEntityID` | `Sales.Store` | `Person.BusinessEntity` | BusinessEntityID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |
| `FK_Store_SalesPerson_SalesPersonID` | `Sales.Store` | `Sales.SalesPerson` | SalesPersonID → BusinessEntityID | `NO_ACTION` | `NO_ACTION` |

## 7. 테이블별 상세 스키마

### dbo.AWBuildVersion

- 행 수: 1
- Primary Key: `[SystemInformationID]`
- 관계: outgoing 0개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SystemInformationID` | `tinyint` | NO | IDENTITY | PK(1) | - |
| 2 | `Database Version` | `nvarchar(25)` | NO | - | - | - |
| 3 | `VersionDate` | `datetime` | NO | - | - | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

### dbo.DatabaseLog

- 행 수: 1,596
- Primary Key: `[DatabaseLogID]`
- 관계: outgoing 0개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `DatabaseLogID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `PostTime` | `datetime` | NO | - | - | - |
| 3 | `DatabaseUser` | `sysname` | NO | - | - | - |
| 4 | `Event` | `sysname` | NO | - | - | - |
| 5 | `Schema` | `sysname` | YES | - | - | - |
| 6 | `Object` | `sysname` | YES | - | - | - |
| 7 | `TSQL` | `nvarchar(max)` | NO | - | - | - |
| 8 | `XmlEvent` | `xml` | NO | - | - | - |

### dbo.ErrorLog

- 행 수: 0
- Primary Key: `[ErrorLogID]`
- 관계: outgoing 0개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ErrorLogID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ErrorTime` | `datetime` | NO | - | - | `(getdate())` |
| 3 | `UserName` | `sysname` | NO | - | - | - |
| 4 | `ErrorNumber` | `int` | NO | - | - | - |
| 5 | `ErrorSeverity` | `int` | YES | - | - | - |
| 6 | `ErrorState` | `int` | YES | - | - | - |
| 7 | `ErrorProcedure` | `nvarchar(126)` | YES | - | - | - |
| 8 | `ErrorLine` | `int` | YES | - | - | - |
| 9 | `ErrorMessage` | `nvarchar(4000)` | NO | - | - | - |

### HumanResources.Department

- 행 수: 16
- Primary Key: `[DepartmentID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `DepartmentID` | `smallint` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `GroupName` | `Name` | NO | - | - | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `HumanResources.EmployeeDepartmentHistory`.`DepartmentID` → 이 테이블

### HumanResources.Employee

- 행 수: 290
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 1개 / incoming 6개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `NationalIDNumber` | `nvarchar(15)` | NO | - | - | - |
| 3 | `LoginID` | `nvarchar(256)` | NO | - | - | - |
| 4 | `OrganizationNode` | `hierarchyid` | YES | - | - | - |
| 5 | `OrganizationLevel` | `smallint` | YES | COMPUTED | - | - |
| 6 | `JobTitle` | `nvarchar(50)` | NO | - | - | - |
| 7 | `BirthDate` | `date` | NO | - | - | - |
| 8 | `MaritalStatus` | `nchar(1)` | NO | - | - | - |
| 9 | `Gender` | `nchar(1)` | NO | - | - | - |
| 10 | `HireDate` | `date` | NO | - | - | - |
| 11 | `SalariedFlag` | `Flag` | NO | - | - | `((1))` |
| 12 | `VacationHours` | `smallint` | NO | - | - | `((0))` |
| 13 | `SickLeaveHours` | `smallint` | NO | - | - | `((0))` |
| 14 | `CurrentFlag` | `Flag` | NO | - | - | `((1))` |
| 15 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 16 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Employee_Person_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `HumanResources.EmployeeDepartmentHistory`.`BusinessEntityID` → 이 테이블
- `HumanResources.EmployeePayHistory`.`BusinessEntityID` → 이 테이블
- `HumanResources.JobCandidate`.`BusinessEntityID` → 이 테이블
- `Production.Document`.`Owner` → 이 테이블
- `Purchasing.PurchaseOrderHeader`.`EmployeeID` → 이 테이블
- `Sales.SalesPerson`.`BusinessEntityID` → 이 테이블

### HumanResources.EmployeeDepartmentHistory

- 행 수: 296
- Primary Key: `[BusinessEntityID], [StartDate], [DepartmentID], [ShiftID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `DepartmentID` | `smallint` | NO | - | PK(3) | - |
| 3 | `ShiftID` | `tinyint` | NO | - | PK(4) | - |
| 4 | `StartDate` | `date` | NO | - | PK(2) | - |
| 5 | `EndDate` | `date` | YES | - | - | - |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_EmployeeDepartmentHistory_Department_DepartmentID`: DepartmentID → DepartmentID → `HumanResources.Department` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_EmployeeDepartmentHistory_Employee_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_EmployeeDepartmentHistory_Shift_ShiftID`: ShiftID → ShiftID → `HumanResources.Shift` (DELETE NO_ACTION, UPDATE NO_ACTION)

### HumanResources.EmployeePayHistory

- 행 수: 316
- Primary Key: `[BusinessEntityID], [RateChangeDate]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `RateChangeDate` | `datetime` | NO | - | PK(2) | - |
| 3 | `Rate` | `money` | NO | - | - | - |
| 4 | `PayFrequency` | `tinyint` | NO | - | - | - |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_EmployeePayHistory_Employee_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)

### HumanResources.JobCandidate

- 행 수: 13
- Primary Key: `[JobCandidateID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `JobCandidateID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `BusinessEntityID` | `int` | YES | - | - | - |
| 3 | `Resume` | `xml` | YES | - | - | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_JobCandidate_Employee_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)

### HumanResources.Shift

- 행 수: 3
- Primary Key: `[ShiftID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ShiftID` | `tinyint` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `StartTime` | `time(7)` | NO | - | - | - |
| 4 | `EndTime` | `time(7)` | NO | - | - | - |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `HumanResources.EmployeeDepartmentHistory`.`ShiftID` → 이 테이블

### Person.Address

- 행 수: 19,614
- Primary Key: `[AddressID]`
- 관계: outgoing 1개 / incoming 3개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `AddressID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `AddressLine1` | `nvarchar(60)` | NO | - | - | - |
| 3 | `AddressLine2` | `nvarchar(60)` | YES | - | - | - |
| 4 | `City` | `nvarchar(30)` | NO | - | - | - |
| 5 | `StateProvinceID` | `int` | NO | - | - | - |
| 6 | `PostalCode` | `nvarchar(15)` | NO | - | - | - |
| 7 | `SpatialLocation` | `geography` | YES | - | - | - |
| 8 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 9 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Address_StateProvince_StateProvinceID`: StateProvinceID → StateProvinceID → `Person.StateProvince` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Person.BusinessEntityAddress`.`AddressID` → 이 테이블
- `Sales.SalesOrderHeader`.`BillToAddressID` → 이 테이블
- `Sales.SalesOrderHeader`.`ShipToAddressID` → 이 테이블

### Person.AddressType

- 행 수: 6
- Primary Key: `[AddressTypeID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `AddressTypeID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Person.BusinessEntityAddress`.`AddressTypeID` → 이 테이블

### Person.BusinessEntity

- 행 수: 20,777
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 0개 / incoming 5개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Person.BusinessEntityAddress`.`BusinessEntityID` → 이 테이블
- `Person.BusinessEntityContact`.`BusinessEntityID` → 이 테이블
- `Person.Person`.`BusinessEntityID` → 이 테이블
- `Purchasing.Vendor`.`BusinessEntityID` → 이 테이블
- `Sales.Store`.`BusinessEntityID` → 이 테이블

### Person.BusinessEntityAddress

- 행 수: 19,614
- Primary Key: `[BusinessEntityID], [AddressID], [AddressTypeID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `AddressID` | `int` | NO | - | PK(2) | - |
| 3 | `AddressTypeID` | `int` | NO | - | PK(3) | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_BusinessEntityAddress_Address_AddressID`: AddressID → AddressID → `Person.Address` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BusinessEntityAddress_AddressType_AddressTypeID`: AddressTypeID → AddressTypeID → `Person.AddressType` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BusinessEntityAddress_BusinessEntity_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.BusinessEntity` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Person.BusinessEntityContact

- 행 수: 909
- Primary Key: `[BusinessEntityID], [PersonID], [ContactTypeID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `PersonID` | `int` | NO | - | PK(2) | - |
| 3 | `ContactTypeID` | `int` | NO | - | PK(3) | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_BusinessEntityContact_BusinessEntity_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.BusinessEntity` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BusinessEntityContact_ContactType_ContactTypeID`: ContactTypeID → ContactTypeID → `Person.ContactType` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BusinessEntityContact_Person_PersonID`: PersonID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Person.ContactType

- 행 수: 20
- Primary Key: `[ContactTypeID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ContactTypeID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Person.BusinessEntityContact`.`ContactTypeID` → 이 테이블

### Person.CountryRegion

- 행 수: 238
- Primary Key: `[CountryRegionCode]`
- 관계: outgoing 0개 / incoming 3개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CountryRegionCode` | `nvarchar(3)` | NO | - | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Person.StateProvince`.`CountryRegionCode` → 이 테이블
- `Sales.CountryRegionCurrency`.`CountryRegionCode` → 이 테이블
- `Sales.SalesTerritory`.`CountryRegionCode` → 이 테이블

### Person.EmailAddress

- 행 수: 19,972
- Primary Key: `[BusinessEntityID], [EmailAddressID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `EmailAddressID` | `int` | NO | IDENTITY | PK(2) | - |
| 3 | `EmailAddress` | `nvarchar(50)` | YES | - | - | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_EmailAddress_Person_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Person.Password

- 행 수: 19,972
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `PasswordHash` | `varchar(128)` | NO | - | - | - |
| 3 | `PasswordSalt` | `varchar(10)` | NO | - | - | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Password_Person_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Person.Person

- 행 수: 19,972
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 1개 / incoming 7개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `PersonType` | `nchar(2)` | NO | - | - | - |
| 3 | `NameStyle` | `NameStyle` | NO | - | - | `((0))` |
| 4 | `Title` | `nvarchar(8)` | YES | - | - | - |
| 5 | `FirstName` | `Name` | NO | - | - | - |
| 6 | `MiddleName` | `Name` | YES | - | - | - |
| 7 | `LastName` | `Name` | NO | - | - | - |
| 8 | `Suffix` | `nvarchar(10)` | YES | - | - | - |
| 9 | `EmailPromotion` | `int` | NO | - | - | `((0))` |
| 10 | `AdditionalContactInfo` | `xml` | YES | - | - | - |
| 11 | `Demographics` | `xml` | YES | - | - | - |
| 12 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 13 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Person_BusinessEntity_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.BusinessEntity` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `HumanResources.Employee`.`BusinessEntityID` → 이 테이블
- `Person.BusinessEntityContact`.`PersonID` → 이 테이블
- `Person.EmailAddress`.`BusinessEntityID` → 이 테이블
- `Person.Password`.`BusinessEntityID` → 이 테이블
- `Person.PersonPhone`.`BusinessEntityID` → 이 테이블
- `Sales.Customer`.`PersonID` → 이 테이블
- `Sales.PersonCreditCard`.`BusinessEntityID` → 이 테이블

### Person.PersonPhone

- 행 수: 19,972
- Primary Key: `[BusinessEntityID], [PhoneNumber], [PhoneNumberTypeID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `PhoneNumber` | `Phone` | NO | - | PK(2) | - |
| 3 | `PhoneNumberTypeID` | `int` | NO | - | PK(3) | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_PersonPhone_Person_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_PersonPhone_PhoneNumberType_PhoneNumberTypeID`: PhoneNumberTypeID → PhoneNumberTypeID → `Person.PhoneNumberType` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Person.PhoneNumberType

- 행 수: 3
- Primary Key: `[PhoneNumberTypeID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `PhoneNumberTypeID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Person.PersonPhone`.`PhoneNumberTypeID` → 이 테이블

### Person.StateProvince

- 행 수: 181
- Primary Key: `[StateProvinceID]`
- 관계: outgoing 2개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `StateProvinceID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `StateProvinceCode` | `nchar(3)` | NO | - | - | - |
| 3 | `CountryRegionCode` | `nvarchar(3)` | NO | - | - | - |
| 4 | `IsOnlyStateProvinceFlag` | `Flag` | NO | - | - | `((1))` |
| 5 | `Name` | `Name` | NO | - | - | - |
| 6 | `TerritoryID` | `int` | NO | - | - | - |
| 7 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 8 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_StateProvince_CountryRegion_CountryRegionCode`: CountryRegionCode → CountryRegionCode → `Person.CountryRegion` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_StateProvince_SalesTerritory_TerritoryID`: TerritoryID → TerritoryID → `Sales.SalesTerritory` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Person.Address`.`StateProvinceID` → 이 테이블
- `Sales.SalesTaxRate`.`StateProvinceID` → 이 테이블

### Production.BillOfMaterials

- 행 수: 2,679
- Primary Key: `[BillOfMaterialsID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BillOfMaterialsID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ProductAssemblyID` | `int` | YES | - | - | - |
| 3 | `ComponentID` | `int` | NO | - | - | - |
| 4 | `StartDate` | `datetime` | NO | - | - | `(getdate())` |
| 5 | `EndDate` | `datetime` | YES | - | - | - |
| 6 | `UnitMeasureCode` | `nchar(3)` | NO | - | - | - |
| 7 | `BOMLevel` | `smallint` | NO | - | - | - |
| 8 | `PerAssemblyQty` | `decimal(8,2)` | NO | - | - | `((1.00))` |
| 9 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_BillOfMaterials_Product_ComponentID`: ComponentID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BillOfMaterials_Product_ProductAssemblyID`: ProductAssemblyID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_BillOfMaterials_UnitMeasure_UnitMeasureCode`: UnitMeasureCode → UnitMeasureCode → `Production.UnitMeasure` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.Culture

- 행 수: 8
- Primary Key: `[CultureID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CultureID` | `nchar(6)` | NO | - | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductModelProductDescriptionCulture`.`CultureID` → 이 테이블

### Production.Document

- 행 수: 13
- Primary Key: `[DocumentNode]`
- 관계: outgoing 1개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `DocumentNode` | `hierarchyid` | NO | - | PK(1) | - |
| 2 | `DocumentLevel` | `smallint` | YES | COMPUTED | - | - |
| 3 | `Title` | `nvarchar(50)` | NO | - | - | - |
| 4 | `Owner` | `int` | NO | - | - | - |
| 5 | `FolderFlag` | `bit` | NO | - | - | `((0))` |
| 6 | `FileName` | `nvarchar(400)` | NO | - | - | - |
| 7 | `FileExtension` | `nvarchar(8)` | NO | - | - | - |
| 8 | `Revision` | `nchar(5)` | NO | - | - | - |
| 9 | `ChangeNumber` | `int` | NO | - | - | `((0))` |
| 10 | `Status` | `tinyint` | NO | - | - | - |
| 11 | `DocumentSummary` | `nvarchar(max)` | YES | - | - | - |
| 12 | `Document` | `varbinary(max)` | YES | - | - | - |
| 13 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 14 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Document_Employee_Owner`: Owner → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Production.ProductDocument`.`DocumentNode` → 이 테이블

### Production.Illustration

- 행 수: 5
- Primary Key: `[IllustrationID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `IllustrationID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Diagram` | `xml` | YES | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductModelIllustration`.`IllustrationID` → 이 테이블

### Production.Location

- 행 수: 14
- Primary Key: `[LocationID]`
- 관계: outgoing 0개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `LocationID` | `smallint` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `CostRate` | `smallmoney` | NO | - | - | `((0.00))` |
| 4 | `Availability` | `decimal(8,2)` | NO | - | - | `((0.00))` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductInventory`.`LocationID` → 이 테이블
- `Production.WorkOrderRouting`.`LocationID` → 이 테이블

### Production.Product

- 행 수: 504
- Primary Key: `[ProductID]`
- 관계: outgoing 4개 / incoming 14개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ProductNumber` | `nvarchar(25)` | NO | - | - | - |
| 4 | `MakeFlag` | `Flag` | NO | - | - | `((1))` |
| 5 | `FinishedGoodsFlag` | `Flag` | NO | - | - | `((1))` |
| 6 | `Color` | `nvarchar(15)` | YES | - | - | - |
| 7 | `SafetyStockLevel` | `smallint` | NO | - | - | - |
| 8 | `ReorderPoint` | `smallint` | NO | - | - | - |
| 9 | `StandardCost` | `money` | NO | - | - | - |
| 10 | `ListPrice` | `money` | NO | - | - | - |
| 11 | `Size` | `nvarchar(5)` | YES | - | - | - |
| 12 | `SizeUnitMeasureCode` | `nchar(3)` | YES | - | - | - |
| 13 | `WeightUnitMeasureCode` | `nchar(3)` | YES | - | - | - |
| 14 | `Weight` | `decimal(8,2)` | YES | - | - | - |
| 15 | `DaysToManufacture` | `int` | NO | - | - | - |
| 16 | `ProductLine` | `nchar(2)` | YES | - | - | - |
| 17 | `Class` | `nchar(2)` | YES | - | - | - |
| 18 | `Style` | `nchar(2)` | YES | - | - | - |
| 19 | `ProductSubcategoryID` | `int` | YES | - | - | - |
| 20 | `ProductModelID` | `int` | YES | - | - | - |
| 21 | `SellStartDate` | `datetime` | NO | - | - | - |
| 22 | `SellEndDate` | `datetime` | YES | - | - | - |
| 23 | `DiscontinuedDate` | `datetime` | YES | - | - | - |
| 24 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 25 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Product_ProductModel_ProductModelID`: ProductModelID → ProductModelID → `Production.ProductModel` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Product_ProductSubcategory_ProductSubcategoryID`: ProductSubcategoryID → ProductSubcategoryID → `Production.ProductSubcategory` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Product_UnitMeasure_SizeUnitMeasureCode`: SizeUnitMeasureCode → UnitMeasureCode → `Production.UnitMeasure` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Product_UnitMeasure_WeightUnitMeasureCode`: WeightUnitMeasureCode → UnitMeasureCode → `Production.UnitMeasure` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Production.BillOfMaterials`.`ComponentID` → 이 테이블
- `Production.BillOfMaterials`.`ProductAssemblyID` → 이 테이블
- `Production.ProductCostHistory`.`ProductID` → 이 테이블
- `Production.ProductDocument`.`ProductID` → 이 테이블
- `Production.ProductInventory`.`ProductID` → 이 테이블
- `Production.ProductListPriceHistory`.`ProductID` → 이 테이블
- `Production.ProductProductPhoto`.`ProductID` → 이 테이블
- `Production.ProductReview`.`ProductID` → 이 테이블
- `Production.TransactionHistory`.`ProductID` → 이 테이블
- `Production.WorkOrder`.`ProductID` → 이 테이블
- `Purchasing.ProductVendor`.`ProductID` → 이 테이블
- `Purchasing.PurchaseOrderDetail`.`ProductID` → 이 테이블
- `Sales.ShoppingCartItem`.`ProductID` → 이 테이블
- `Sales.SpecialOfferProduct`.`ProductID` → 이 테이블

### Production.ProductCategory

- 행 수: 4
- Primary Key: `[ProductCategoryID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductCategoryID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductSubcategory`.`ProductCategoryID` → 이 테이블

### Production.ProductCostHistory

- 행 수: 395
- Primary Key: `[ProductID], [StartDate]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `StartDate` | `datetime` | NO | - | PK(2) | - |
| 3 | `EndDate` | `datetime` | YES | - | - | - |
| 4 | `StandardCost` | `money` | NO | - | - | - |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductCostHistory_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductDescription

- 행 수: 762
- Primary Key: `[ProductDescriptionID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductDescriptionID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Description` | `nvarchar(400)` | NO | - | - | - |
| 3 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductModelProductDescriptionCulture`.`ProductDescriptionID` → 이 테이블

### Production.ProductDocument

- 행 수: 32
- Primary Key: `[ProductID], [DocumentNode]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `DocumentNode` | `hierarchyid` | NO | - | PK(2) | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductDocument_Document_DocumentNode`: DocumentNode → DocumentNode → `Production.Document` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductDocument_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductInventory

- 행 수: 1,069
- Primary Key: `[ProductID], [LocationID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `LocationID` | `smallint` | NO | - | PK(2) | - |
| 3 | `Shelf` | `nvarchar(10)` | NO | - | - | - |
| 4 | `Bin` | `tinyint` | NO | - | - | - |
| 5 | `Quantity` | `smallint` | NO | - | - | `((0))` |
| 6 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 7 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductInventory_Location_LocationID`: LocationID → LocationID → `Production.Location` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductInventory_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductListPriceHistory

- 행 수: 395
- Primary Key: `[ProductID], [StartDate]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `StartDate` | `datetime` | NO | - | PK(2) | - |
| 3 | `EndDate` | `datetime` | YES | - | - | - |
| 4 | `ListPrice` | `money` | NO | - | - | - |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductListPriceHistory_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductModel

- 행 수: 128
- Primary Key: `[ProductModelID]`
- 관계: outgoing 0개 / incoming 3개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductModelID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `CatalogDescription` | `xml` | YES | - | - | - |
| 4 | `Instructions` | `xml` | YES | - | - | - |
| 5 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.Product`.`ProductModelID` → 이 테이블
- `Production.ProductModelIllustration`.`ProductModelID` → 이 테이블
- `Production.ProductModelProductDescriptionCulture`.`ProductModelID` → 이 테이블

### Production.ProductModelIllustration

- 행 수: 7
- Primary Key: `[ProductModelID], [IllustrationID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductModelID` | `int` | NO | - | PK(1) | - |
| 2 | `IllustrationID` | `int` | NO | - | PK(2) | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductModelIllustration_Illustration_IllustrationID`: IllustrationID → IllustrationID → `Production.Illustration` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductModelIllustration_ProductModel_ProductModelID`: ProductModelID → ProductModelID → `Production.ProductModel` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductModelProductDescriptionCulture

- 행 수: 762
- Primary Key: `[ProductModelID], [ProductDescriptionID], [CultureID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductModelID` | `int` | NO | - | PK(1) | - |
| 2 | `ProductDescriptionID` | `int` | NO | - | PK(2) | - |
| 3 | `CultureID` | `nchar(6)` | NO | - | PK(3) | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductModelProductDescriptionCulture_Culture_CultureID`: CultureID → CultureID → `Production.Culture` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductModelProductDescriptionCulture_ProductDescription_ProductDescriptionID`: ProductDescriptionID → ProductDescriptionID → `Production.ProductDescription` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductModelProductDescriptionCulture_ProductModel_ProductModelID`: ProductModelID → ProductModelID → `Production.ProductModel` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductPhoto

- 행 수: 101
- Primary Key: `[ProductPhotoID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductPhotoID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ThumbNailPhoto` | `varbinary(max)` | YES | - | - | - |
| 3 | `ThumbnailPhotoFileName` | `nvarchar(50)` | YES | - | - | - |
| 4 | `LargePhoto` | `varbinary(max)` | YES | - | - | - |
| 5 | `LargePhotoFileName` | `nvarchar(50)` | YES | - | - | - |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.ProductProductPhoto`.`ProductPhotoID` → 이 테이블

### Production.ProductProductPhoto

- 행 수: 504
- Primary Key: `[ProductID], [ProductPhotoID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `ProductPhotoID` | `int` | NO | - | PK(2) | - |
| 3 | `Primary` | `Flag` | NO | - | - | `((0))` |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductProductPhoto_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductProductPhoto_ProductPhoto_ProductPhotoID`: ProductPhotoID → ProductPhotoID → `Production.ProductPhoto` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductReview

- 행 수: 4
- Primary Key: `[ProductReviewID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductReviewID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | - | - |
| 3 | `ReviewerName` | `Name` | NO | - | - | - |
| 4 | `ReviewDate` | `datetime` | NO | - | - | `(getdate())` |
| 5 | `EmailAddress` | `nvarchar(50)` | NO | - | - | - |
| 6 | `Rating` | `int` | NO | - | - | - |
| 7 | `Comments` | `nvarchar(3850)` | YES | - | - | - |
| 8 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductReview_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.ProductSubcategory

- 행 수: 37
- Primary Key: `[ProductSubcategoryID]`
- 관계: outgoing 1개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductSubcategoryID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ProductCategoryID` | `int` | NO | - | - | - |
| 3 | `Name` | `Name` | NO | - | - | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductSubcategory_ProductCategory_ProductCategoryID`: ProductCategoryID → ProductCategoryID → `Production.ProductCategory` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Production.Product`.`ProductSubcategoryID` → 이 테이블

### Production.ScrapReason

- 행 수: 16
- Primary Key: `[ScrapReasonID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ScrapReasonID` | `smallint` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.WorkOrder`.`ScrapReasonID` → 이 테이블

### Production.TransactionHistory

- 행 수: 113,443
- Primary Key: `[TransactionID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `TransactionID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | - | - |
| 3 | `ReferenceOrderID` | `int` | NO | - | - | - |
| 4 | `ReferenceOrderLineID` | `int` | NO | - | - | `((0))` |
| 5 | `TransactionDate` | `datetime` | NO | - | - | `(getdate())` |
| 6 | `TransactionType` | `nchar(1)` | NO | - | - | - |
| 7 | `Quantity` | `int` | NO | - | - | - |
| 8 | `ActualCost` | `money` | NO | - | - | - |
| 9 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_TransactionHistory_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Production.TransactionHistoryArchive

- 행 수: 89,253
- Primary Key: `[TransactionID]`
- 관계: outgoing 0개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `TransactionID` | `int` | NO | - | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | - | - |
| 3 | `ReferenceOrderID` | `int` | NO | - | - | - |
| 4 | `ReferenceOrderLineID` | `int` | NO | - | - | `((0))` |
| 5 | `TransactionDate` | `datetime` | NO | - | - | `(getdate())` |
| 6 | `TransactionType` | `nchar(1)` | NO | - | - | - |
| 7 | `Quantity` | `int` | NO | - | - | - |
| 8 | `ActualCost` | `money` | NO | - | - | - |
| 9 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

### Production.UnitMeasure

- 행 수: 38
- Primary Key: `[UnitMeasureCode]`
- 관계: outgoing 0개 / incoming 4개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `UnitMeasureCode` | `nchar(3)` | NO | - | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Production.BillOfMaterials`.`UnitMeasureCode` → 이 테이블
- `Production.Product`.`SizeUnitMeasureCode` → 이 테이블
- `Production.Product`.`WeightUnitMeasureCode` → 이 테이블
- `Purchasing.ProductVendor`.`UnitMeasureCode` → 이 테이블

### Production.WorkOrder

- 행 수: 72,591
- Primary Key: `[WorkOrderID]`
- 관계: outgoing 2개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `WorkOrderID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | - | - |
| 3 | `OrderQty` | `int` | NO | - | - | - |
| 4 | `StockedQty` | `int` | NO | COMPUTED | - | - |
| 5 | `ScrappedQty` | `smallint` | NO | - | - | - |
| 6 | `StartDate` | `datetime` | NO | - | - | - |
| 7 | `EndDate` | `datetime` | YES | - | - | - |
| 8 | `DueDate` | `datetime` | NO | - | - | - |
| 9 | `ScrapReasonID` | `smallint` | YES | - | - | - |
| 10 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_WorkOrder_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_WorkOrder_ScrapReason_ScrapReasonID`: ScrapReasonID → ScrapReasonID → `Production.ScrapReason` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Production.WorkOrderRouting`.`WorkOrderID` → 이 테이블

### Production.WorkOrderRouting

- 행 수: 67,131
- Primary Key: `[WorkOrderID], [ProductID], [OperationSequence]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `WorkOrderID` | `int` | NO | - | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | PK(2) | - |
| 3 | `OperationSequence` | `smallint` | NO | - | PK(3) | - |
| 4 | `LocationID` | `smallint` | NO | - | - | - |
| 5 | `ScheduledStartDate` | `datetime` | NO | - | - | - |
| 6 | `ScheduledEndDate` | `datetime` | NO | - | - | - |
| 7 | `ActualStartDate` | `datetime` | YES | - | - | - |
| 8 | `ActualEndDate` | `datetime` | YES | - | - | - |
| 9 | `ActualResourceHrs` | `decimal(9,4)` | YES | - | - | - |
| 10 | `PlannedCost` | `money` | NO | - | - | - |
| 11 | `ActualCost` | `money` | YES | - | - | - |
| 12 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_WorkOrderRouting_Location_LocationID`: LocationID → LocationID → `Production.Location` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_WorkOrderRouting_WorkOrder_WorkOrderID`: WorkOrderID → WorkOrderID → `Production.WorkOrder` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Purchasing.ProductVendor

- 행 수: 460
- Primary Key: `[ProductID], [BusinessEntityID]`
- 관계: outgoing 3개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ProductID` | `int` | NO | - | PK(1) | - |
| 2 | `BusinessEntityID` | `int` | NO | - | PK(2) | - |
| 3 | `AverageLeadTime` | `int` | NO | - | - | - |
| 4 | `StandardPrice` | `money` | NO | - | - | - |
| 5 | `LastReceiptCost` | `money` | YES | - | - | - |
| 6 | `LastReceiptDate` | `datetime` | YES | - | - | - |
| 7 | `MinOrderQty` | `int` | NO | - | - | - |
| 8 | `MaxOrderQty` | `int` | NO | - | - | - |
| 9 | `OnOrderQty` | `int` | YES | - | - | - |
| 10 | `UnitMeasureCode` | `nchar(3)` | NO | - | - | - |
| 11 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ProductVendor_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductVendor_UnitMeasure_UnitMeasureCode`: UnitMeasureCode → UnitMeasureCode → `Production.UnitMeasure` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_ProductVendor_Vendor_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Purchasing.Vendor` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Purchasing.PurchaseOrderDetail

- 행 수: 8,845
- Primary Key: `[PurchaseOrderID], [PurchaseOrderDetailID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `PurchaseOrderID` | `int` | NO | - | PK(1) | - |
| 2 | `PurchaseOrderDetailID` | `int` | NO | IDENTITY | PK(2) | - |
| 3 | `DueDate` | `datetime` | NO | - | - | - |
| 4 | `OrderQty` | `smallint` | NO | - | - | - |
| 5 | `ProductID` | `int` | NO | - | - | - |
| 6 | `UnitPrice` | `money` | NO | - | - | - |
| 7 | `LineTotal` | `money` | NO | COMPUTED | - | - |
| 8 | `ReceivedQty` | `decimal(8,2)` | NO | - | - | - |
| 9 | `RejectedQty` | `decimal(8,2)` | NO | - | - | - |
| 10 | `StockedQty` | `decimal(9,2)` | NO | COMPUTED | - | - |
| 11 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_PurchaseOrderDetail_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_PurchaseOrderDetail_PurchaseOrderHeader_PurchaseOrderID`: PurchaseOrderID → PurchaseOrderID → `Purchasing.PurchaseOrderHeader` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Purchasing.PurchaseOrderHeader

- 행 수: 4,012
- Primary Key: `[PurchaseOrderID]`
- 관계: outgoing 3개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `PurchaseOrderID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `RevisionNumber` | `tinyint` | NO | - | - | `((0))` |
| 3 | `Status` | `tinyint` | NO | - | - | `((1))` |
| 4 | `EmployeeID` | `int` | NO | - | - | - |
| 5 | `VendorID` | `int` | NO | - | - | - |
| 6 | `ShipMethodID` | `int` | NO | - | - | - |
| 7 | `OrderDate` | `datetime` | NO | - | - | `(getdate())` |
| 8 | `ShipDate` | `datetime` | YES | - | - | - |
| 9 | `SubTotal` | `money` | NO | - | - | `((0.00))` |
| 10 | `TaxAmt` | `money` | NO | - | - | `((0.00))` |
| 11 | `Freight` | `money` | NO | - | - | `((0.00))` |
| 12 | `TotalDue` | `money` | NO | COMPUTED | - | - |
| 13 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_PurchaseOrderHeader_Employee_EmployeeID`: EmployeeID → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_PurchaseOrderHeader_ShipMethod_ShipMethodID`: ShipMethodID → ShipMethodID → `Purchasing.ShipMethod` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_PurchaseOrderHeader_Vendor_VendorID`: VendorID → BusinessEntityID → `Purchasing.Vendor` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Purchasing.PurchaseOrderDetail`.`PurchaseOrderID` → 이 테이블

### Purchasing.ShipMethod

- 행 수: 5
- Primary Key: `[ShipMethodID]`
- 관계: outgoing 0개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ShipMethodID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ShipBase` | `money` | NO | - | - | `((0.00))` |
| 4 | `ShipRate` | `money` | NO | - | - | `((0.00))` |
| 5 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Purchasing.PurchaseOrderHeader`.`ShipMethodID` → 이 테이블
- `Sales.SalesOrderHeader`.`ShipMethodID` → 이 테이블

### Purchasing.Vendor

- 행 수: 104
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 1개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `AccountNumber` | `AccountNumber` | NO | - | - | - |
| 3 | `Name` | `Name` | NO | - | - | - |
| 4 | `CreditRating` | `tinyint` | NO | - | - | - |
| 5 | `PreferredVendorStatus` | `Flag` | NO | - | - | `((1))` |
| 6 | `ActiveFlag` | `Flag` | NO | - | - | `((1))` |
| 7 | `PurchasingWebServiceURL` | `nvarchar(1024)` | YES | - | - | - |
| 8 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Vendor_BusinessEntity_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.BusinessEntity` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Purchasing.ProductVendor`.`BusinessEntityID` → 이 테이블
- `Purchasing.PurchaseOrderHeader`.`VendorID` → 이 테이블

### Sales.CountryRegionCurrency

- 행 수: 109
- Primary Key: `[CountryRegionCode], [CurrencyCode]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CountryRegionCode` | `nvarchar(3)` | NO | - | PK(1) | - |
| 2 | `CurrencyCode` | `nchar(3)` | NO | - | PK(2) | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_CountryRegionCurrency_CountryRegion_CountryRegionCode`: CountryRegionCode → CountryRegionCode → `Person.CountryRegion` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_CountryRegionCurrency_Currency_CurrencyCode`: CurrencyCode → CurrencyCode → `Sales.Currency` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.CreditCard

- 행 수: 19,118
- Primary Key: `[CreditCardID]`
- 관계: outgoing 0개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CreditCardID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `CardType` | `nvarchar(50)` | NO | - | - | - |
| 3 | `CardNumber` | `nvarchar(25)` | NO | - | - | - |
| 4 | `ExpMonth` | `tinyint` | NO | - | - | - |
| 5 | `ExpYear` | `smallint` | NO | - | - | - |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Sales.PersonCreditCard`.`CreditCardID` → 이 테이블
- `Sales.SalesOrderHeader`.`CreditCardID` → 이 테이블

### Sales.Currency

- 행 수: 105
- Primary Key: `[CurrencyCode]`
- 관계: outgoing 0개 / incoming 3개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CurrencyCode` | `nchar(3)` | NO | - | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Sales.CountryRegionCurrency`.`CurrencyCode` → 이 테이블
- `Sales.CurrencyRate`.`FromCurrencyCode` → 이 테이블
- `Sales.CurrencyRate`.`ToCurrencyCode` → 이 테이블

### Sales.CurrencyRate

- 행 수: 13,532
- Primary Key: `[CurrencyRateID]`
- 관계: outgoing 2개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CurrencyRateID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `CurrencyRateDate` | `datetime` | NO | - | - | - |
| 3 | `FromCurrencyCode` | `nchar(3)` | NO | - | - | - |
| 4 | `ToCurrencyCode` | `nchar(3)` | NO | - | - | - |
| 5 | `AverageRate` | `money` | NO | - | - | - |
| 6 | `EndOfDayRate` | `money` | NO | - | - | - |
| 7 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_CurrencyRate_Currency_FromCurrencyCode`: FromCurrencyCode → CurrencyCode → `Sales.Currency` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_CurrencyRate_Currency_ToCurrencyCode`: ToCurrencyCode → CurrencyCode → `Sales.Currency` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.SalesOrderHeader`.`CurrencyRateID` → 이 테이블

### Sales.Customer

- 행 수: 19,820
- Primary Key: `[CustomerID]`
- 관계: outgoing 3개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `CustomerID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `PersonID` | `int` | YES | - | - | - |
| 3 | `StoreID` | `int` | YES | - | - | - |
| 4 | `TerritoryID` | `int` | YES | - | - | - |
| 5 | `AccountNumber` | `varchar(10)` | NO | COMPUTED | - | - |
| 6 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 7 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Customer_Person_PersonID`: PersonID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Customer_SalesTerritory_TerritoryID`: TerritoryID → TerritoryID → `Sales.SalesTerritory` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Customer_Store_StoreID`: StoreID → BusinessEntityID → `Sales.Store` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.SalesOrderHeader`.`CustomerID` → 이 테이블

### Sales.PersonCreditCard

- 행 수: 19,118
- Primary Key: `[BusinessEntityID], [CreditCardID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `CreditCardID` | `int` | NO | - | PK(2) | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_PersonCreditCard_CreditCard_CreditCardID`: CreditCardID → CreditCardID → `Sales.CreditCard` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_PersonCreditCard_Person_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.Person` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SalesOrderDetail

- 행 수: 121,317
- Primary Key: `[SalesOrderID], [SalesOrderDetailID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SalesOrderID` | `int` | NO | - | PK(1) | - |
| 2 | `SalesOrderDetailID` | `int` | NO | IDENTITY | PK(2) | - |
| 3 | `CarrierTrackingNumber` | `nvarchar(25)` | YES | - | - | - |
| 4 | `OrderQty` | `smallint` | NO | - | - | - |
| 5 | `ProductID` | `int` | NO | - | - | - |
| 6 | `SpecialOfferID` | `int` | NO | - | - | - |
| 7 | `UnitPrice` | `money` | NO | - | - | - |
| 8 | `UnitPriceDiscount` | `money` | NO | - | - | `((0.0))` |
| 9 | `LineTotal` | `numeric(38,6)` | NO | COMPUTED | - | - |
| 10 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 11 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesOrderDetail_SalesOrderHeader_SalesOrderID`: SalesOrderID → SalesOrderID → `Sales.SalesOrderHeader` (DELETE CASCADE, UPDATE NO_ACTION)
- `FK_SalesOrderDetail_SpecialOfferProduct_SpecialOfferIDProductID`: SpecialOfferID → SpecialOfferID, ProductID → ProductID → `Sales.SpecialOfferProduct` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SalesOrderHeader

- 행 수: 31,465
- Primary Key: `[SalesOrderID]`
- 관계: outgoing 8개 / incoming 2개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SalesOrderID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `RevisionNumber` | `tinyint` | NO | - | - | `((0))` |
| 3 | `OrderDate` | `datetime` | NO | - | - | `(getdate())` |
| 4 | `DueDate` | `datetime` | NO | - | - | - |
| 5 | `ShipDate` | `datetime` | YES | - | - | - |
| 6 | `Status` | `tinyint` | NO | - | - | `((1))` |
| 7 | `OnlineOrderFlag` | `Flag` | NO | - | - | `((1))` |
| 8 | `SalesOrderNumber` | `nvarchar(25)` | NO | COMPUTED | - | - |
| 9 | `PurchaseOrderNumber` | `OrderNumber` | YES | - | - | - |
| 10 | `AccountNumber` | `AccountNumber` | YES | - | - | - |
| 11 | `CustomerID` | `int` | NO | - | - | - |
| 12 | `SalesPersonID` | `int` | YES | - | - | - |
| 13 | `TerritoryID` | `int` | YES | - | - | - |
| 14 | `BillToAddressID` | `int` | NO | - | - | - |
| 15 | `ShipToAddressID` | `int` | NO | - | - | - |
| 16 | `ShipMethodID` | `int` | NO | - | - | - |
| 17 | `CreditCardID` | `int` | YES | - | - | - |
| 18 | `CreditCardApprovalCode` | `varchar(15)` | YES | - | - | - |
| 19 | `CurrencyRateID` | `int` | YES | - | - | - |
| 20 | `SubTotal` | `money` | NO | - | - | `((0.00))` |
| 21 | `TaxAmt` | `money` | NO | - | - | `((0.00))` |
| 22 | `Freight` | `money` | NO | - | - | `((0.00))` |
| 23 | `TotalDue` | `money` | NO | COMPUTED | - | - |
| 24 | `Comment` | `nvarchar(128)` | YES | - | - | - |
| 25 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 26 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesOrderHeader_Address_BillToAddressID`: BillToAddressID → AddressID → `Person.Address` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_Address_ShipToAddressID`: ShipToAddressID → AddressID → `Person.Address` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_CreditCard_CreditCardID`: CreditCardID → CreditCardID → `Sales.CreditCard` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_CurrencyRate_CurrencyRateID`: CurrencyRateID → CurrencyRateID → `Sales.CurrencyRate` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_Customer_CustomerID`: CustomerID → CustomerID → `Sales.Customer` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_SalesPerson_SalesPersonID`: SalesPersonID → BusinessEntityID → `Sales.SalesPerson` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_SalesTerritory_TerritoryID`: TerritoryID → TerritoryID → `Sales.SalesTerritory` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesOrderHeader_ShipMethod_ShipMethodID`: ShipMethodID → ShipMethodID → `Purchasing.ShipMethod` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.SalesOrderDetail`.`SalesOrderID` → 이 테이블
- `Sales.SalesOrderHeaderSalesReason`.`SalesOrderID` → 이 테이블

### Sales.SalesOrderHeaderSalesReason

- 행 수: 27,647
- Primary Key: `[SalesOrderID], [SalesReasonID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SalesOrderID` | `int` | NO | - | PK(1) | - |
| 2 | `SalesReasonID` | `int` | NO | - | PK(2) | - |
| 3 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesOrderHeaderSalesReason_SalesOrderHeader_SalesOrderID`: SalesOrderID → SalesOrderID → `Sales.SalesOrderHeader` (DELETE CASCADE, UPDATE NO_ACTION)
- `FK_SalesOrderHeaderSalesReason_SalesReason_SalesReasonID`: SalesReasonID → SalesReasonID → `Sales.SalesReason` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SalesPerson

- 행 수: 17
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 2개 / incoming 4개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `TerritoryID` | `int` | YES | - | - | - |
| 3 | `SalesQuota` | `money` | YES | - | - | - |
| 4 | `Bonus` | `money` | NO | - | - | `((0.00))` |
| 5 | `CommissionPct` | `smallmoney` | NO | - | - | `((0.00))` |
| 6 | `SalesYTD` | `money` | NO | - | - | `((0.00))` |
| 7 | `SalesLastYear` | `money` | NO | - | - | `((0.00))` |
| 8 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 9 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesPerson_Employee_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `HumanResources.Employee` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesPerson_SalesTerritory_TerritoryID`: TerritoryID → TerritoryID → `Sales.SalesTerritory` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.SalesOrderHeader`.`SalesPersonID` → 이 테이블
- `Sales.SalesPersonQuotaHistory`.`BusinessEntityID` → 이 테이블
- `Sales.SalesTerritoryHistory`.`BusinessEntityID` → 이 테이블
- `Sales.Store`.`SalesPersonID` → 이 테이블

### Sales.SalesPersonQuotaHistory

- 행 수: 163
- Primary Key: `[BusinessEntityID], [QuotaDate]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `QuotaDate` | `datetime` | NO | - | PK(2) | - |
| 3 | `SalesQuota` | `money` | NO | - | - | - |
| 4 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 5 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesPersonQuotaHistory_SalesPerson_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Sales.SalesPerson` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SalesReason

- 행 수: 10
- Primary Key: `[SalesReasonID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SalesReasonID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `ReasonType` | `Name` | NO | - | - | - |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Sales.SalesOrderHeaderSalesReason`.`SalesReasonID` → 이 테이블

### Sales.SalesTaxRate

- 행 수: 29
- Primary Key: `[SalesTaxRateID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SalesTaxRateID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `StateProvinceID` | `int` | NO | - | - | - |
| 3 | `TaxType` | `tinyint` | NO | - | - | - |
| 4 | `TaxRate` | `smallmoney` | NO | - | - | `((0.00))` |
| 5 | `Name` | `Name` | NO | - | - | - |
| 6 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 7 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesTaxRate_StateProvince_StateProvinceID`: StateProvinceID → StateProvinceID → `Person.StateProvince` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SalesTerritory

- 행 수: 10
- Primary Key: `[TerritoryID]`
- 관계: outgoing 1개 / incoming 5개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `TerritoryID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `CountryRegionCode` | `nvarchar(3)` | NO | - | - | - |
| 4 | `Group` | `nvarchar(50)` | NO | - | - | - |
| 5 | `SalesYTD` | `money` | NO | - | - | `((0.00))` |
| 6 | `SalesLastYear` | `money` | NO | - | - | `((0.00))` |
| 7 | `CostYTD` | `money` | NO | - | - | `((0.00))` |
| 8 | `CostLastYear` | `money` | NO | - | - | `((0.00))` |
| 9 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 10 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesTerritory_CountryRegion_CountryRegionCode`: CountryRegionCode → CountryRegionCode → `Person.CountryRegion` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Person.StateProvince`.`TerritoryID` → 이 테이블
- `Sales.Customer`.`TerritoryID` → 이 테이블
- `Sales.SalesOrderHeader`.`TerritoryID` → 이 테이블
- `Sales.SalesPerson`.`TerritoryID` → 이 테이블
- `Sales.SalesTerritoryHistory`.`TerritoryID` → 이 테이블

### Sales.SalesTerritoryHistory

- 행 수: 17
- Primary Key: `[BusinessEntityID], [StartDate], [TerritoryID]`
- 관계: outgoing 2개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `TerritoryID` | `int` | NO | - | PK(3) | - |
| 3 | `StartDate` | `datetime` | NO | - | PK(2) | - |
| 4 | `EndDate` | `datetime` | YES | - | - | - |
| 5 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SalesTerritoryHistory_SalesPerson_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Sales.SalesPerson` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SalesTerritoryHistory_SalesTerritory_TerritoryID`: TerritoryID → TerritoryID → `Sales.SalesTerritory` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.ShoppingCartItem

- 행 수: 3
- Primary Key: `[ShoppingCartItemID]`
- 관계: outgoing 1개 / incoming 0개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `ShoppingCartItemID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `ShoppingCartID` | `nvarchar(50)` | NO | - | - | - |
| 3 | `Quantity` | `int` | NO | - | - | `((1))` |
| 4 | `ProductID` | `int` | NO | - | - | - |
| 5 | `DateCreated` | `datetime` | NO | - | - | `(getdate())` |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_ShoppingCartItem_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)

### Sales.SpecialOffer

- 행 수: 16
- Primary Key: `[SpecialOfferID]`
- 관계: outgoing 0개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SpecialOfferID` | `int` | NO | IDENTITY | PK(1) | - |
| 2 | `Description` | `nvarchar(255)` | NO | - | - | - |
| 3 | `DiscountPct` | `smallmoney` | NO | - | - | `((0.00))` |
| 4 | `Type` | `nvarchar(50)` | NO | - | - | - |
| 5 | `Category` | `nvarchar(50)` | NO | - | - | - |
| 6 | `StartDate` | `datetime` | NO | - | - | - |
| 7 | `EndDate` | `datetime` | NO | - | - | - |
| 8 | `MinQty` | `int` | NO | - | - | `((0))` |
| 9 | `MaxQty` | `int` | YES | - | - | - |
| 10 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 11 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

참조받는 관계(incoming):

- `Sales.SpecialOfferProduct`.`SpecialOfferID` → 이 테이블

### Sales.SpecialOfferProduct

- 행 수: 538
- Primary Key: `[SpecialOfferID], [ProductID]`
- 관계: outgoing 2개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `SpecialOfferID` | `int` | NO | - | PK(1) | - |
| 2 | `ProductID` | `int` | NO | - | PK(2) | - |
| 3 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 4 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_SpecialOfferProduct_Product_ProductID`: ProductID → ProductID → `Production.Product` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_SpecialOfferProduct_SpecialOffer_SpecialOfferID`: SpecialOfferID → SpecialOfferID → `Sales.SpecialOffer` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.SalesOrderDetail`.`SpecialOfferID`, `ProductID` → 이 테이블

### Sales.Store

- 행 수: 701
- Primary Key: `[BusinessEntityID]`
- 관계: outgoing 2개 / incoming 1개

| # | 컬럼 | 타입 | NULL | 속성 | Key | 기본값 |
|---:|---|---|---|---|---|---|
| 1 | `BusinessEntityID` | `int` | NO | - | PK(1) | - |
| 2 | `Name` | `Name` | NO | - | - | - |
| 3 | `SalesPersonID` | `int` | YES | - | - | - |
| 4 | `Demographics` | `xml` | YES | - | - | - |
| 5 | `rowguid` | `uniqueidentifier` | NO | - | - | `(newid())` |
| 6 | `ModifiedDate` | `datetime` | NO | - | - | `(getdate())` |

외부키(outgoing):

- `FK_Store_BusinessEntity_BusinessEntityID`: BusinessEntityID → BusinessEntityID → `Person.BusinessEntity` (DELETE NO_ACTION, UPDATE NO_ACTION)
- `FK_Store_SalesPerson_SalesPersonID`: SalesPersonID → BusinessEntityID → `Sales.SalesPerson` (DELETE NO_ACTION, UPDATE NO_ACTION)

참조받는 관계(incoming):

- `Sales.Customer`.`StoreID` → 이 테이블

## 8. 조회 시 주의할 데이터

- `Person.Password`는 비밀번호 해시·salt 성격의 데이터를 포함하므로 일반 질의 컨텍스트에서 제외한다.
- `Sales.CreditCard`, `Sales.PersonCreditCard`는 샘플 데이터라도 민감정보 테이블로 분류해 접근 정책을 적용한다.
- `HumanResources.EmployeePayHistory`는 급여 정보이므로 역할 기반 ACL 대상이다.
- `dbo.DatabaseLog`는 DDL 변경 이력을 포함하며 일반 업무 질의 대상이 아니다.
- 애플리케이션은 `sa` 대신 최소 권한 read-only 로그인을 사용해야 한다.

## 9. 문서 생성 기준

- 테이블/컬럼: `sys.tables`, `sys.schemas`, `sys.columns`, `sys.types`
- PK: `sys.key_constraints`, `sys.index_columns`
- FK: `sys.foreign_keys`, `sys.foreign_key_columns`
- 행 수: `sys.dm_db_partition_stats`에서 `index_id IN (0, 1)`
- 원본 데이터베이스: Docker SQL Server의 `AdventureWorks2022`
- 생성일: 2026-07-14 (Asia/Seoul)
